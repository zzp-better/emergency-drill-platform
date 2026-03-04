# 🧪 测试快速入门指南

## 立即开始测试

### 1️⃣ 安装依赖

```bash
cd emergency-drill-platform
pip install -r requirements.txt
```

### 2️⃣ 运行测试

```bash
# 方式 1: 使用测试脚本（推荐）
python run_tests.py all

# 方式 2: 直接使用 pytest
pytest
```

### 3️⃣ 查看结果

测试完成后，你会看到：
- ✅ 通过的测试数量
- ❌ 失败的测试（如果有）
- 📊 代码覆盖率报告

覆盖率 HTML 报告位置：`htmlcov/index.html`

## 📋 常用命令

```bash
# 只运行单元测试（快速）
python run_tests.py unit

# 只运行集成测试
python run_tests.py integration

# 运行快速测试（跳过慢速测试）
python run_tests.py quick

# 详细输出
python run_tests.py all -v

# 运行特定测试
pytest tests/unit/test_monitor.py
pytest tests/unit/test_monitor.py::TestPrometheusClient::test_init_without_auth
```

## 📊 测试覆盖率

当前目标：**≥ 80%**

查看覆盖率报告：
```bash
# 生成并查看 HTML 报告
pytest --cov=src --cov-report=html
# 然后在浏览器中打开 htmlcov/index.html
```

## 🎯 测试结构

```
tests/
├── conftest.py              # 共享配置和 fixtures
├── unit/                    # 单元测试（快速，隔离）
│   ├── test_monitor.py
│   ├── test_chaos_injector.py
│   ├── test_monitor_checker.py
│   └── test_chaos_mesh_injector.py
└── integration/             # 集成测试（完整流程）
    ├── test_drill_workflow.py
    └── test_prometheus_integration.py
```

## 🔍 测试内容

### 单元测试覆盖
- ✅ Prometheus 客户端（查询告警、指标）
- ✅ 混沌注入器（Pod 删除、网络延迟、CPU/内存压力）
- ✅ 监控检查器（告警验证、等待触发）
- ✅ Chaos Mesh 注入器（混沌实验管理）

### 集成测试覆盖
- ✅ 端到端混沌演练流程
- ✅ Prometheus 监控集成
- ✅ 多步骤混沌注入
- ✅ 错误处理和恢复

## 🛠️ 开发工作流

### 编写新功能时

1. **先写测试**（TDD 方式）
   ```bash
   # 创建测试文件
   touch tests/unit/test_new_feature.py
   ```

2. **运行测试（应该失败）**
   ```bash
   pytest tests/unit/test_new_feature.py
   ```

3. **实现功能**
   ```python
   # 在 src/ 中实现功能
   ```

4. **再次运行测试（应该通过）**
   ```bash
   pytest tests/unit/test_new_feature.py
   ```

5. **检查覆盖率**
   ```bash
   pytest --cov=src --cov-report=term-missing
   ```

### 修复 Bug 时

1. **写一个失败的测试来重现 Bug**
2. **修复代码**
3. **确保测试通过**
4. **运行所有测试确保没有破坏其他功能**

## 🚀 CI/CD 集成

项目已配置 GitHub Actions，每次 push 或 PR 时自动运行：
- ✅ 代码格式检查
- ✅ 单元测试
- ✅ 集成测试
- ✅ 覆盖率检查（≥ 80%）

配置文件：`.github/workflows/tests.yml`

## 📚 更多信息

详细文档请查看：[tests/README.md](tests/README.md)

## ❓ 常见问题

**Q: 测试运行很慢怎么办？**
```bash
# 只运行快速测试
python run_tests.py quick

# 或并行运行（需要安装 pytest-xdist）
pip install pytest-xdist
pytest -n auto
```

**Q: 如何调试失败的测试？**
```bash
# 显示详细输出
pytest -vv

# 失败时进入调试器
pytest --pdb

# 显示打印输出
pytest -s
```

**Q: 如何跳过某些测试？**
```python
@pytest.mark.skip(reason="暂时跳过")
def test_something():
    pass
```

## 🎉 开始测试吧！

```bash
python run_tests.py all
```
