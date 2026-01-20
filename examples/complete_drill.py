"""
完整应急演练示例

功能：
1. 注入故障（删除 Pod）
2. 验证监控告警是否触发
3. 生成演练报告

这是一个完整的应急演练流程演示
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


def run_complete_drill():
    """运行完整的应急演练"""

    print()
    print("╔═══════════════════════════════════════════════════════════════════╗")
    print("║            应急演练自动化平台 - 完整演练流程                       ║")
    print("║         Emergency Drill Automation Platform                      ║")
    print("╚═══════════════════════════════════════════════════════════════════╝")

    # ========== 第一步：配置参数 ==========
    print_section("第一步：配置演练参数")

    namespace = input("目标命名空间 [default]: ").strip() or "default"
    pod_name = input("目标 Pod 名称: ").strip()

    if not pod_name:
        print("❌ 错误：Pod 名称不能为空")
        return

    prometheus_url = input("Prometheus URL [http://localhost:9090]: ").strip() or "http://localhost:9090"
    alert_name = input("预期告警名称 [可选，回车跳过]: ").strip()

    # 演练配置总结
    print()
    print("📋 演练配置：")
    print(f"  命名空间: {namespace}")
    print(f"  目标 Pod: {pod_name}")
    print(f"  Prometheus: {prometheus_url}")
    print(f"  预期告警: {alert_name if alert_name else '未配置'}")
    print()

    confirm = input("确认执行演练？(yes/no): ").strip().lower()
    if confirm != "yes":
        print("❌ 演练已取消")
        return

    # ========== 第二步：初始化组件 ==========
    print_section("第二步：初始化组件")

    try:
        injector = ChaosInjector()
        print("✅ 故障注入器初始化成功")
    except Exception as e:
        print(f"❌ 故障注入器初始化失败: {e}")
        return

    if alert_name:
        try:
            checker = MonitorChecker(prometheus_url)
            print("✅ 监控验证器初始化成功")
        except Exception as e:
            print(f"❌ 监控验证器初始化失败: {e}")
            checker = None
    else:
        checker = None
        print("⚠️  未配置告警验证，跳过监控验证器初始化")

    # ========== 第三步：执行故障注入 ==========
    print_section("第三步：执行故障注入")

    drill_start_time = datetime.now()
    print(f"🕐 演练开始时间: {drill_start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    print(f"🔥 正在注入故障: 删除 Pod {namespace}/{pod_name}")
    print("-" * 70)

    inject_result = injector.delete_pod(namespace, pod_name)

    print()
    if inject_result['success']:
        print("✅ 故障注入成功")
        print(f"  恢复时间: {inject_result['recovery_time']} 秒")
    else:
        print("❌ 故障注入失败")
        print(f"  错误信息: {inject_result['message']}")
        return

    # ========== 第四步：验证监控告警 ==========
    if alert_name and checker:
        print_section("第四步：验证监控告警")

        print(f"🔍 等待告警触发: {alert_name}")
        print("  (超时时间: 180 秒)")
        print()

        alert_result = checker.wait_for_alert(
            alert_name=alert_name,
            timeout=180,
            check_interval=10
        )

        print()
        if alert_result['triggered']:
            print("✅ 告警验证通过")
            print(f"  触发时间: {alert_result['trigger_time']}")
            print(f"  等待时长: {alert_result['wait_time']} 秒")
        else:
            print("❌ 告警验证失败")
            print(f"  原因: {alert_result['message']}")
    else:
        print_section("第四步：验证监控告警（已跳过）")
        alert_result = None

    # ========== 第五步：生成演练报告 ==========
    print_section("第五步：生成演练报告")

    drill_end_time = datetime.now()
    total_time = (drill_end_time - drill_start_time).total_seconds()

    report = generate_report(
        namespace=namespace,
        pod_name=pod_name,
        start_time=drill_start_time,
        end_time=drill_end_time,
        inject_result=inject_result,
        alert_result=alert_result
    )

    print(report)

    # 保存报告
    save = input("\n是否保存报告？(yes/no): ").strip().lower()
    if save == "yes":
        report_dir = "../reports"
        os.makedirs(report_dir, exist_ok=True)

        filename = f"drill_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        filepath = os.path.join(report_dir, filename)

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(report)

        print(f"✅ 报告已保存: {filepath}")

    # ========== 完成 ==========
    print()
    print("╔═══════════════════════════════════════════════════════════════════╗")
    print("║                  🎉 演练完成！                                     ║")
    print("╚═══════════════════════════════════════════════════════════════════╝")
    print()


def generate_report(namespace, pod_name, start_time, end_time, inject_result, alert_result):
    """生成演练报告"""

    total_time = int((end_time - start_time).total_seconds())

    report = f"""# 应急演练报告

## 基本信息

- **演练场景**: Pod 崩溃应急演练
- **目标对象**: {namespace}/{pod_name}
- **开始时间**: {start_time.strftime('%Y-%m-%d %H:%M:%S')}
- **结束时间**: {end_time.strftime('%Y-%m-%d %H:%M:%S')}
- **总耗时**: {total_time} 秒
- **执行人**: 应急演练自动化平台

---

## 演练结果

### 故障注入

- **执行状态**: {'✅ 成功' if inject_result['success'] else '❌ 失败'}
- **注入时间**: {inject_result['inject_time']}
- **Pod 恢复时间**: {inject_result.get('recovery_time', 'N/A')} 秒
- **详细信息**: {inject_result['message']}

"""

    if alert_result:
        report += f"""### 监控告警验证

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

    # 判断演练是否通过
    passed = inject_result['success']
    if alert_result:
        passed = passed and alert_result['triggered']

    if passed:
        report += """✅ **演练通过**

本次应急演练成功完成，系统表现符合预期：
- Pod 在故障后能够自动恢复
"""
        if alert_result and alert_result['triggered']:
            report += "- 监控告警正常触发\n"
    else:
        report += """❌ **演练失败**

本次应急演练发现以下问题：
"""
        if not inject_result['success']:
            report += "- 故障注入失败，请检查 Kubernetes 连接和权限\n"
        if alert_result and not alert_result['triggered']:
            report += "- 监控告警未触发，请检查告警规则配置\n"

    report += """
---

## 改进建议

1. 定期执行应急演练，确保系统自愈能力
2. 优化 Pod 恢复时间，考虑增加副本数
3. 完善监控告警规则，缩短告警响应时间
4. 建立应急预案知识库，积累故障处理经验

---

*本报告由应急演练自动化平台自动生成*
*生成时间: {end_time.strftime('%Y-%m-%d %H:%M:%S')}*
"""

    return report


if __name__ == "__main__":
    try:
        run_complete_drill()
    except KeyboardInterrupt:
        print("\n\n❌ 演练已中断")
    except Exception as e:
        print(f"\n\n❌ 发生错误: {e}")
        import traceback
        traceback.print_exc()
