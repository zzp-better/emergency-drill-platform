# 测试文档

## 📋 目录

- [快速开始](#快速开始)
- [测试结构](#测试结构)
- [运行测试](#运行测试)
- [编写测试](#编写测试)
- [测试覆盖率](#测试覆盖率)
- [CI/CD 集成](#cicd-集成)

## 🚀 快速开始

### 安装测试依赖

```bash
pip install -r requirements.txt
```

### 运行所有测试

```bash
# 使用 pytest 直接运行
pytest

# 或使用测试脚本
python run_tests.py all
```

## 📁 测试结构

```
tests/
├── conftest.py                 # Pytest 配置和共享 fixtures
├── unit/                       # 单元测试
│   ├── test_monitor.py
│   ├── test_chaos_injector.py
│   ├── test_monitor_checker.py
│   └── test_chaos_mesh_injector.py
└── integration/                # 集成测试
    ├── test_drill_workflow.py
    └── test_prometheus_integration.py
```

## 🧪 运行测试

### 使用测试脚本（推荐）

```bash
# 运行所有测试
python run_tests.py all

# 只运行单元测试
python run_tests.py unit

# 只运行集成测试
python run_tests.py integration

# 运行快速测试（跳过慢速测试）
python run_tests.py quick

# 运行特定关键字的测试
python run_tests.py all -k "test_pod_kill"

# 详细输出
python run_tests.py all -v
```

### 使用 pytest 直接运行

```bash
# 运行所有测试
pytest

# 运行单元测试
pytest -m unit

# 运行集成测试
pytest -m integration

# 运行特定文件
pytest tests/unit/test_monitor.py

# 运行特定测试函数
pytest tests/unit/test_monitor.py::TestPrometheusClient::test_init_without_auth

# 详细输出
pytest -v

# 显示打印输出
pytest -s

# 失败时立即停止
pytest -x

# 并行运行（需要 pytest-xdist）
pytest -n auto
```

### 按标记运行

```bash
# 运行单元测试
pytest -m unit

# 运行集成测试
pytest -m integration

# 运行慢速测试
pytest -m slow

# 跳过慢速测试
pytest -m "not slow"

# 运行需要 Kubernetes 的测试
pytest -m k8s

# 运行需要 Prometheus 的测试
pytest -m prometheus
```

## ✍️ 编写测试

### 单元测试示例

```python
import pytest
from unittest.mock import Mock, patch

@pytest.mark.unit
class TestMyClass:
    """测试 MyClass 类"""

    def test_basic_functionality(self):
        """测试基本功能"""
        obj = MyClass()
        result = obj.method()
        assert result == expected_value

    @patch('module.external_dependency')
    def test_with_mock(self, mock_dep):
        """测试使用 mock"""
        mock_dep.return_value = "mocked"
        obj = MyClass()
        result = obj.method_using_dependency()
        assert result == "expected"
```

### 集成测试示例

```python
import pytest

@pytest.mark.integration
class TestIntegration:
    """集成测试"""

    def test_end_to_end_workflow(self):
        """测试端到端工作流"""
        # 设置
        setup_environment()

        # 执行
        result = run_workflow()

        # 验证
        assert result.success is True

        # 清理
        cleanup_environment()
```

### 使用 Fixtures

```python
@pytest.fixture
def sample_data():
    """提供测试数据"""
    return {"key": "value"}

def test_with_fixture(sample_data):
    """使用 fixture 的测试"""
    assert sample_data["key"] == "value"
```

## 📊 测试覆盖率

### 生成覆盖率报告

```bash
# 生成 HTML 报告
pytest --cov=src --cov-report=html

# 生成终端报告
pytest --cov=src --cov-report=term-missing

# 生成 XML 报告（用于 CI）
pytest --cov=src --cov-report=xml

# 设置最低覆盖率要求
pytest --cov=src --cov-fail-under=80
```

### 查看覆盖率报告

HTML 报告位置：`htmlcov/index.html`

```bash
# Windows
start htmlcov/index.html

# Linux/Mac
open htmlcov/index.html
```

### 覆盖率目标

- **总体覆盖率**: ≥ 80%
- **核心模块**: ≥ 90%
- **工具函数**: ≥ 70%

## 🔧 测试配置

### pytest.ini

项目根目录的 `pytest.ini` 文件包含测试配置：

```ini
[pytest]
testpaths = tests
addopts = -v --cov=src --cov-report=html
markers =
    unit: 单元测试
    integration: 集成测试
    slow: 慢速测试
```

### conftest.py

`tests/conftest.py` 包含共享的 fixtures 和配置：

- Mock fixtures (Prometheus, Kubernetes)
- 测试数据 fixtures
- 自动清理 fixtures

## 🚦 CI/CD 集成

### GitHub Actions 示例

创建 `.github/workflows/tests.yml`:

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v3

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.9'

    - name: Install dependencies
      run: |
        pip install -r requirements.txt

    - name: Run tests
      run: |
        pytest --cov=src --cov-report=xml

    - name: Upload coverage
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
```

## 🐛 调试测试

### 使用 pdb

```python
def test_debug():
    import pdb; pdb.set_trace()
    # 测试代码
```

### 使用 pytest 调试选项

```bash
# 失败时进入 pdb
pytest --pdb

# 第一个失败时进入 pdb
pytest -x --pdb

# 显示局部变量
pytest -l
```

## 📝 最佳实践

### 1. 测试命名

- 测试文件: `test_*.py` 或 `*_test.py`
- 测试类: `Test*`
- 测试函数: `test_*`

### 2. 测试组织

- 每个模块一个测试文件
- 使用类组织相关测试
- 使用描述性的测试名称

### 3. 断言

```python
# 好的断言
assert result == expected, f"Expected {expected}, got {result}"

# 使用 pytest 断言
assert result is True
assert "error" in response
assert len(items) == 3
```

### 4. Mock 使用

```python
# Mock 外部依赖
@patch('module.external_api')
def test_with_mock(mock_api):
    mock_api.return_value = "mocked"
    # 测试代码

# Mock 多个依赖
@patch('module.dep1')
@patch('module.dep2')
def test_multiple_mocks(mock_dep2, mock_dep1):
    # 注意：装饰器顺序与参数顺序相反
    pass
```

### 5. 测试隔离

- 每个测试应该独立运行
- 使用 fixtures 进行设置和清理
- 避免测试之间的依赖

## 🔍 常见问题

### Q: 如何跳过某个测试？

```python
@pytest.mark.skip(reason="暂时跳过")
def test_something():
    pass

@pytest.mark.skipif(sys.version_info < (3, 8), reason="需要 Python 3.8+")
def test_something_else():
    pass
```

### Q: 如何测试异常？

```python
def test_exception():
    with pytest.raises(ValueError):
        raise ValueError("error")

    with pytest.raises(ValueError, match="specific error"):
        raise ValueError("specific error message")
```

### Q: 如何参数化测试？

```python
@pytest.mark.parametrize("input,expected", [
    (1, 2),
    (2, 4),
    (3, 6),
])
def test_multiply_by_two(input, expected):
    assert input * 2 == expected
```

## 📚 参考资源

- [Pytest 官方文档](https://docs.pytest.org/)
- [Pytest-cov 文档](https://pytest-cov.readthedocs.io/)
- [Python Mock 文档](https://docs.python.org/3/library/unittest.mock.html)
- [测试最佳实践](https://docs.python-guide.org/writing/tests/)

## 🤝 贡献

编写新测试时，请确保：

1. ✅ 测试通过
2. ✅ 代码覆盖率不降低
3. ✅ 遵循命名约定
4. ✅ 添加适当的标记
5. ✅ 包含文档字符串
