#!/usr/bin/env python3
"""
测试运行脚本
提供便捷的测试执行命令
"""
import sys
import subprocess
import argparse
from pathlib import Path


def run_command(cmd, description):
    """运行命令并显示结果"""
    print(f"\n{'='*60}")
    print(f"🔧 {description}")
    print(f"{'='*60}")
    print(f"命令: {' '.join(cmd)}\n")

    result = subprocess.run(cmd, cwd=Path(__file__).parent)

    if result.returncode != 0:
        print(f"\n❌ {description} 失败")
        return False
    else:
        print(f"\n✅ {description} 成功")
        return True


def main():
    parser = argparse.ArgumentParser(description="测试运行脚本")
    parser.add_argument(
        "test_type",
        nargs="?",
        default="all",
        choices=["all", "unit", "integration", "coverage", "quick", "slow"],
        help="测试类型"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="详细输出"
    )
    parser.add_argument(
        "-k", "--keyword",
        type=str,
        help="运行匹配关键字的测试"
    )
    parser.add_argument(
        "--no-cov",
        action="store_true",
        help="不生成覆盖率报告"
    )

    args = parser.parse_args()

    # 基础命令
    base_cmd = ["pytest"]

    if args.verbose:
        base_cmd.append("-vv")

    if args.keyword:
        base_cmd.extend(["-k", args.keyword])

    # 根据测试类型构建命令
    if args.test_type == "all":
        cmd = base_cmd.copy()
        if not args.no_cov:
            cmd.extend(["--cov=src", "--cov-report=html", "--cov-report=term-missing"])
        description = "运行所有测试"

    elif args.test_type == "unit":
        cmd = base_cmd + ["-m", "unit", "tests/unit/"]
        description = "运行单元测试"

    elif args.test_type == "integration":
        cmd = base_cmd + ["-m", "integration", "tests/integration/"]
        description = "运行集成测试"

    elif args.test_type == "coverage":
        cmd = base_cmd + [
            "--cov=src",
            "--cov-report=html",
            "--cov-report=term-missing",
            "--cov-fail-under=80"
        ]
        description = "运行测试并生成覆盖率报告"

    elif args.test_type == "quick":
        cmd = base_cmd + ["-m", "not slow", "--no-cov"]
        description = "运行快速测试（跳过慢速测试）"

    elif args.test_type == "slow":
        cmd = base_cmd + ["-m", "slow"]
        description = "运行慢速测试"

    # 运行测试
    success = run_command(cmd, description)

    # 显示覆盖率报告位置
    if not args.no_cov and args.test_type in ["all", "coverage"]:
        print(f"\n📊 覆盖率报告已生成:")
        print(f"   HTML: {Path(__file__).parent / 'htmlcov' / 'index.html'}")

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
