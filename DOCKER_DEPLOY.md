# Docker 部署流程

## 一、前置准备

### 1. 安装 Docker
```bash
# macOS
brew install docker docker-compose

# 或下载 Docker Desktop
# https://www.docker.com/products/docker-desktop
```

### 2. 确认 Docker 运行
```bash
docker --version
docker-compose --version
```

### 3. 准备 kubeconfig
确保你的 `~/.kube/config` 文件存在且可以访问 Kubernetes 集群：
```bash
kubectl cluster-info
```

---

## 二、配置环境变量

### 1. 复制环境变量模板
```bash
cd emergency-drill-platform
cp .env.example .env
```

### 2. 修改 .env（可选）
```bash
# 默认配置已经可以直接使用，如需修改：
vim .env
```

默认端口：
- 应用：8501
- Prometheus：9090
- Pushgateway：9091
- Grafana：3000

---

## 三、构建和启动服务

### 方式一：一键启动（推荐）
```bash
# 构建镜像并启动所有服务
docker-compose up -d --build
```

### 方式二：分步执行
```bash
# 1. 构建应用镜像
docker build -t emergency-drill-platform:latest .

# 2. 启动所有服务
docker-compose up -d
```

---

## 四、验证部署

### 1. 查看容器状态
```bash
docker-compose ps
```

应该看到 4 个容器都是 `Up` 状态：
- edp-app
- edp-prometheus
- edp-pushgateway
- edp-grafana

### 2. 查看应用日志
```bash
# 查看所有服务日志
docker-compose logs -f

# 只查看应用日志
docker-compose logs -f app
```

### 3. 访问服务
打开浏览器访问：
- **应急演练平台**: http://localhost:8501
- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000 (用户名: admin, 密码: admin123)

---

## 五、常用操作

### 停止服务
```bash
docker-compose stop
```

### 重启服务
```bash
docker-compose restart
```

### 停止并删除容器
```bash
docker-compose down
```

### 停止并删除容器+数据卷
```bash
docker-compose down -v
```

### 查看资源占用
```bash
docker stats
```

### 进入容器调试
```bash
docker exec -it edp-app bash
```

---

## 六、故障排查

### 问题1：容器启动失败
```bash
# 查看详细日志
docker-compose logs app

# 常见原因：
# - 端口被占用：修改 .env 中的端口
# - kubeconfig 路径错误：检查 KUBECONFIG_PATH
```

### 问题2：无法连接 Kubernetes
```bash
# 进入容器检查
docker exec -it edp-app bash
kubectl get nodes

# 如果失败，检查：
# 1. 宿主机 ~/.kube/config 是否正确
# 2. docker-compose.yml 中的卷挂载路径
```

### 问题3：Prometheus 无数据
```bash
# 检查 Pushgateway 是否正常
curl http://localhost:9091/metrics

# 检查 Prometheus 配置
docker exec -it edp-prometheus cat /etc/prometheus/prometheus.yml
```

---

## 七、更新应用

### 1. 拉取最新代码
```bash
git pull
```

### 2. 重新构建并启动
```bash
docker-compose up -d --build
```

---

## 八、生产环境建议

### 1. 修改默认密码
编辑 `.env`：
```bash
GRAFANA_PASSWORD=your_secure_password
```

### 2. 数据备份
```bash
# 备份数据卷
docker run --rm -v edp-data:/data -v $(pwd):/backup \
  alpine tar czf /backup/edp-data-backup.tar.gz -C /data .
```

### 3. 资源限制
在 `docker-compose.yml` 中添加：
```yaml
services:
  app:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
```

### 4. 启用 HTTPS
使用 Nginx 反向代理或 Traefik。

---

## 快速命令参考

```bash
# 启动
docker-compose up -d --build

# 查看状态
docker-compose ps

# 查看日志
docker-compose logs -f app

# 停止
docker-compose down

# 完全清理（包括数据）
docker-compose down -v
docker system prune -a
```
