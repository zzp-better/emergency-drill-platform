#!/bin/bash
# 测试套件安装和验证脚本

echo "=========================================="
echo "🧪 测试套件安装和验证"
echo "=========================================="
echo ""

# 检查 Python 版本
echo "1️⃣ 检查 Python 版本..."
python --version
echo ""

# 安装依赖
echo "2️⃣ 安装测试依赖..."
pip install -r requirements.txt
echo ""

# 验证 pytest 安装
echo "3️⃣ 验证 pytest 安装..."
python -m pytest --version
echo ""

# 列出测试文件
echo "4️⃣ 测试文件列表..."
echo "单元测试:"
ls -la tests/unit/test_*.py 2>/dev/null || dir tests\unit\test_*.py
echo ""
echo "集成测试:"
ls -la tests/integration/test_*.py 2>/dev/null || dir tests\integration\test_*.py
echo ""

# 运行测试（收集模式，不实际执行）
echo "5️⃣ 收集测试用例..."
python -m pytest --collect-only
echo ""

# 运行快速测试
echo "6️⃣ 运行快速测试（跳过慢速测试）..."
python run_tests.py quick
echo ""

echo "=========================================="
echo "✅ 安装和验证完成！"
echo "=========================================="
echo ""
echo "下一步："
echo "  - 运行所有测试: python run_tests.py all"
echo "  - 查看文档: cat TESTING.md"
echo "  - 查看覆盖率: open htmlcov/index.html"
echo ""
