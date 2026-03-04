"""
Chaos Mesh 故障注入演练示例

功能：
1. 演示如何使用 Chaos Mesh 注入各种故障
2. 演示如何从配置文件加载场景
3. 演示如何验证监控告警
4. 自动生成演练报告

前置条件：
1. 已安装 Chaos Mesh（参考: https://chaos-mesh.org/docs/installation）
2. kubectl 已配置
3. 有相应的 Kubernetes 权限
4. Prometheus 已部署并配置告警规则

作者：应急运维工程师
"""

import sys
import os
import time
from datetime import datetime

# 添加 src 目录到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from chaos_injector import ChaosInjector
from monitor_checker import MonitorChecker


def print_section(title):
    """打印章节标题"""
    print()
    print("=" * 70)
    print(f"  {title}")
    print("=" * 70)
    print()


def example_cpu_stress():
    """示例 1：CPU 压测演练"""
    print_section("示例 1：CPU 压测演练")

    # 初始化故障注入器（使用 Chaos Mesh）
    injector = ChaosInjector(use_chaos_mesh=True)

    # 配置参数
    namespace = "default"
    pod_name = input("目标 Pod 名称: ").strip()

    if not pod_name:
        print("❌ Pod 名称不能为空")
        return

    # 执行 CPU 压测
    print(f"🔥 正在注入 CPU 压测故障: {namespace}/{pod_name}")
    print("-" * 70)

    result = injector.inject_cpu_stress(
        namespace=namespace,
        pod_name=pod_name,
        cpu_count=2,
        memory_size="100Mi",
        duration="60s"
    )

    print()
    if result['success']:
        print("✅ CPU 压测故障注入成功")
        print(f"  故障名称: {result.get('chaos_name', 'N/A')}")
    else:
        print("❌ CPU 压测故障注入失败")
        print(f"  错误信息: {result['message']}")

    return result


def example_network_delay():
    """示例 2：网络延迟演练"""
    print_section("示例 2：网络延迟演练")

    # 初始化故障注入器（使用 Chaos Mesh）
    injector = ChaosInjector(use_chaos_mesh=True)

    # 配置参数
    namespace = "default"
    pod_name = input("目标 Pod 名称: ").strip()

    if not pod_name:
        print("❌ Pod 名称不能为空")
        return

    # 执行网络延迟
    print(f"🔥 正在注入网络延迟故障: {namespace}/{pod_name}")
    print("-" * 70)

    result = injector.inject_network_delay(
        namespace=namespace,
        pod_name=pod_name,
        latency="100ms",
        jitter="10ms",
        duration="60s"
    )

    print()
    if result['success']:
        print("✅ 网络延迟故障注入成功")
        print(f"  故障名称: {result.get('chaos_name', 'N/A')}")
    else:
        print("❌ 网络延迟故障注入失败")
        print(f"  错误信息: {result['message']}")

    return result


def example_disk_failure():
    """示例 3：磁盘故障演练"""
    print_section("示例 3：磁盘故障演练")

    # 初始化故障注入器（使用 Chaos Mesh）
    injector = ChaosInjector(use_chaos_mesh=True)

    # 配置参数
    namespace = "default"
    pod_name = input("目标 Pod 名称: ").strip()

    if not pod_name:
        print("❌ Pod 名称不能为空")
        return

    # 执行磁盘故障
    print(f"🔥 正在注入磁盘故障: {namespace}/{pod_name}")
    print("-" * 70)

    result = injector.inject_disk_failure(
        namespace=namespace,
        pod_name=pod_name,
        path="/var/log",
        fault_type="disk_fill",
        size="1Gi",
        duration="60s"
    )

    print()
    if result['success']:
        print("✅ 磁盘故障注入成功")
        print(f"  故障名称: {result.get('chaos_name', 'N/A')}")
    else:
        print("❌ 磁盘故障注入失败")
        print(f"  错误信息: {result['message']}")

    return result


def example_from_config():
    """示例 4：从配置文件注入故障"""
    print_section("示例 4：从配置文件注入故障")

    # 初始化故障注入器（使用 Chaos Mesh）
    injector = ChaosInjector(use_chaos_mesh=True)

    # 列出可用的场景配置
    scenarios_dir = os.path.join(os.path.dirname(__file__), '..', 'scenarios')
    scenarios = [
        "cpu_stress.yaml",
        "network_delay.yaml",
        "disk_io.yaml"
    ]

    print("可用的场景配置：")
    for i, scenario in enumerate(scenarios, 1):
        print(f"  {i}. {scenario}")

    choice = input("\n选择场景配置 (1-3): ").strip()

    if not choice or not choice.isdigit() or int(choice) < 1 or int(choice) > len(scenarios):
        print("❌ 无效的选择")
        return

    config_file = os.path.join(scenarios_dir, scenarios[int(choice) - 1])

    # 执行演练
    print(f"📋 加载场景配置: {config_file}")
    print("-" * 70)

    result = injector.inject_from_config(config_file)

    print()
    if result['success']:
        print("✅ 故障注入成功")
        print(f"  场景类型: {result.get('chaos_type', 'N/A')}")
        print(f"  故障名称: {result.get('chaos_name', 'N/A')}")
    else:
        print("❌ 故障注入失败")
        print(f"  错误信息: {result['message']}")

    return result


def example_complete_drill():
    """示例 5：完整的 Chaos Mesh 演练流程"""
    print_section("示例 5：完整的 Chaos Mesh 演练流程")

    # 配置参数
    namespace = "default"
    pod_name = input("目标 Pod 名称: ").strip()

    if not pod_name:
        print("❌ Pod 名称不能为空")
        return

    prometheus_url = input("Prometheus URL [http://localhost:9090]: ").strip() or "http://localhost:9090"
    alert_name = input("预期告警名称 [可选，回车跳过]: ").strip()

    # 初始化组件
    print()
    print("正在初始化组件...")
    injector = ChaosInjector(use_chaos_mesh=True)
    checker = MonitorChecker(prometheus_url) if alert_name else None

    print("✅ 组件初始化完成")

    # 执行故障注入
    print()
    print("请选择故障类型：")
    print("  1. CPU 压测")
    print("  2. 网络延迟")
    print("  3. 磁盘故障")

    choice = input("选择故障类型 (1-3): ").strip()

    drill_start_time = datetime.now()
    inject_result = None

    if choice == "1":
        print(f"\n🔥 正在注入 CPU 压测故障: {namespace}/{pod_name}")
        inject_result = injector.inject_cpu_stress(
            namespace=namespace,
            pod_name=pod_name,
            cpu_count=2,
            duration="60s"
        )
    elif choice == "2":
        print(f"\n🔥 正在注入网络延迟故障: {namespace}/{pod_name}")
        inject_result = injector.inject_network_delay(
            namespace=namespace,
            pod_name=pod_name,
            latency="100ms",
            duration="60s"
        )
    elif choice == "3":
        print(f"\n🔥 正在注入磁盘故障: {namespace}/{pod_name}")
        inject_result = injector.inject_disk_failure(
            namespace=namespace,
            pod_name=pod_name,
            fault_type="disk_fill",
            duration="60s"
        )
    else:
        print("❌ 无效的选择")
        return

    print()
    if inject_result['success']:
        print("✅ 故障注入成功")
    else:
        print("❌ 故障注入失败")
        print(f"  错误信息: {inject_result['message']}")
        return

    # 验证监控告警
    alert_result = None
    if alert_name and checker:
        print()
        print(f"🔍 等待告警触发: {alert_name}")
        alert_result = checker.wait_for_alert(
            alert_name=alert_name,
            timeout=180,
            check_interval=10
        )

        print()
        if alert_result['triggered']:
            print("✅ 告警验证通过")
        else:
            print("❌ 告警验证失败")

    # 生成报告
    print()
    print_section("演练报告")

    drill_end_time = datetime.now()
    total_time = int((drill_end_time - drill_start_time).total_seconds())

    report = f"""# Chaos Mesh 应急演练报告

## 基本信息

- **演练时间**: {drill_start_time.strftime('%Y-%m-%d %H:%M:%S')}
- **目标对象**: {namespace}/{pod_name}
- **总耗时**: {total_time} 秒
- **执行人**: 应急演练自动化平台

---

## 故障注入结果

- **故障类型**: {inject_result.get('chaos_type', 'N/A')}
- **故障名称**: {inject_result.get('chaos_name', 'N/A')}
- **执行状态**: {'✅ 成功' if inject_result['success'] else '❌ 失败'}
- **注入时间**: {inject_result.get('inject_time', 'N/A')}
- **详细信息**: {inject_result['message']}

"""

    if alert_result:
        report += f"""## 监控告警验证

- **告警名称**: {alert_result['alert_name']}
- **触发状态**: {'✅ 已触发' if alert_result['triggered'] else '❌ 未触发'}
- **等待时长**: {alert_result['wait_time']} 秒
"""
        if alert_result['triggered']:
            report += f"- **触发时间**: {alert_result['trigger_time']}\n"

        report += f"- **详细信息**: {alert_result['message']}\n"

    report += """
---

## 结论

"""

    passed = inject_result['success']
    if alert_result:
        passed = passed and alert_result['triggered']

    if passed:
        report += """✅ **演练通过**

本次 Chaos Mesh 应急演练成功完成，系统表现符合预期。
"""
    else:
        report += """❌ **演练失败**

本次 Chaos Mesh 应急演练发现以下问题，需要进一步排查。
"""

    report += """
---

## 改进建议

1. 定期执行 Chaos Mesh 故障注入演练，提升系统韧性
2. 完善监控告警规则，缩短故障发现时间
3. 优化故障恢复流程，提高系统自愈能力
4. 建立故障处理知识库，积累应急处理经验

---

*本报告由应急演练自动化平台自动生成*
*生成时间: """ + drill_end_time.strftime('%Y-%m-%d %H:%M:%S') + "*"

    print(report)

    # 保存报告
    save = input("\n是否保存报告？(yes/no): ").strip().lower()
    if save == "yes":
        report_dir = "../reports"
        os.makedirs(report_dir, exist_ok=True)

        filename = f"chaos_mesh_drill_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        filepath = os.path.join(report_dir, filename)

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(report)

        print(f"✅ 报告已保存: {filepath}")


def main():
    """主函数"""
    print()
    print("╔═══════════════════════════════════════════════════════════════════╗")
    print("║        应急演练自动化平台 - Chaos Mesh 故障注入示例             ║")
    print("║         Emergency Drill Automation Platform                      ║")
    print("╚═══════════════════════════════════════════════════════════════════╝")
    print()

    print("请选择要运行的示例：")
    print("  1. CPU 压测演练")
    print("  2. 网络延迟演练")
    print("  3. 磁盘故障演练")
    print("  4. 从配置文件注入故障")
    print("  5. 完整的 Chaos Mesh 演练流程")
    print()

    choice = input("选择示例 (1-5): ").strip()

    try:
        if choice == "1":
            example_cpu_stress()
        elif choice == "2":
            example_network_delay()
        elif choice == "3":
            example_disk_failure()
        elif choice == "4":
            example_from_config()
        elif choice == "5":
            example_complete_drill()
        else:
            print("❌ 无效的选择")

        print()
        print("╔═══════════════════════════════════════════════════════════════════╗")
        print("║                  🎉 演练完成！                                     ║")
        print("╚═══════════════════════════════════════════════════════════════════╝")
        print()

    except KeyboardInterrupt:
        print("\n\n❌ 演练已中断")
    except Exception as e:
        print(f"\n\n❌ 发生错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
