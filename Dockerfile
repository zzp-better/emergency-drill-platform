# ─────────────────────────────────────────────
# 构建阶段：安装依赖
# ─────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /app

# 安装系统依赖（kubernetes 客户端需要 gcc）
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# 先复制依赖文件，利用 Docker 层缓存
COPY requirements.txt .

# 只安装运行时依赖（排除测试 / 代码质量工具）
RUN pip install --no-cache-dir --prefix=/install \
    streamlit \
    pandas \
    apscheduler \
    kubernetes \
    pyopenssl \
    requests \
    PyYAML \
    coloredlogs \
    click \
    python-dateutil


# ─────────────────────────────────────────────
# 运行阶段：精简镜像
# ─────────────────────────────────────────────
FROM python:3.11-slim AS runtime

LABEL maintainer="emergency-drill-platform"
LABEL description="应急演练智能平台 - Emergency Drill Platform"

WORKDIR /app

# 从构建阶段复制已安装的包
COPY --from=builder /install /usr/local

# 复制项目源码
COPY src/       ./src/
COPY web_ui.py  .
COPY scenarios/ ./scenarios/

# 创建数据目录（SQLite 数据库 + 演练报告）
RUN mkdir -p data reports

# 创建非 root 用户运行（安全最佳实践）
RUN useradd -m -u 1000 appuser \
    && chown -R appuser:appuser /app
USER appuser

# Streamlit 端口
EXPOSE 8501

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8501/_stcore/health')" || exit 1

# 启动命令
ENTRYPOINT ["streamlit", "run", "web_ui.py", \
            "--server.port=8501", \
            "--server.address=0.0.0.0", \
            "--server.headless=true", \
            "--browser.gatherUsageStats=false"]
