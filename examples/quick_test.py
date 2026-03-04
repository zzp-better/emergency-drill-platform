"""
快速交互测试脚本

用于快速测试应急演练平台的功能，无需复杂配置。

使用方法：
    python examples/quick_test.py

作者：应急运维工程师
"""

import sys
import os

# 添加 src 目录到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from chaos_injector import ChaosInjector
from monitor_checker import MonitorChecker


def print_header(title):
    """打印标题"""
    print()
    print("=" * 70)
    print(f"  {title}")
    print("=" * 70)
    print()


def print_menu():
    """打印菜单"""
    print("请选择要执行的操作：")
    print()
    print("【基础功能】")
    print("  1. 列出所有 Pod")
    print("  2. 删除指定 Pod（模拟崩溃）")
    print()
    print("【Chaos Mesh 故障注入】（需要先安装 Chaos Mesh）")
    print("  3. CPU 压测")
    print("  4. 网络延迟")
    print("  5. 磁盘故障")
    print()
    print("【监控验证】")
    print("  6. 查询当前活跃告警")
    print("  7. 等待指定告警触发")
    print()
    print("  0. 退出")
    print()


def list_pods():
    """列出所有 Pod"""
    print_header("列出所有 Pod")

    namespace = input("输入命名空间 [default]: ").strip() or "default"

    try:
        injector = ChaosInjector()
        pods = injector.list_pods(namespace)

        if not pods:
            print("❌ 没有找到 Pod")
            return

        print(f"✓ 找到 {len(pods)} 个 Pod：")
        print()
        print(f"{'序号':<6} {'Pod 名称':<40} {'状态':<12} {'节点':<20}")
        print("-" * 78)

        for i, pod in enumerate(pods, 1):
            print(f"{i:<6} {pod['name']:<40} {pod['status']:<12} {str(pod['node']):<20}")

    except Exception as e:
        print(f"❌ 错误: {e}")


def delete_pod():
    """删除指定 Pod"""
    print_header("删除指定 Pod")

    namespace = input("输入命名空间 [default]: ").strip() or "default"
    pod_name = input("输入 Pod 名称: ").strip()

    if not pod_name:
        print("❌ Pod 名称不能为空")
        return

    confirm = input(f"确认删除 {namespace}/{pod_name}？(yes/no): ").strip().lower()
    if confirm != "yes":
        print("❌ 已取消")
        return

    try:
        injector = ChaosInjector()
        print()
        print("正在删除 Pod...")
        result = injector.delete_pod(namespace, pod_name)

        print()
        if result['success']:
            print("✅ Pod 删除成功")
            if result.get('recovery_time'):
                print(f"   Pod 在 {result['recovery_time']} 秒后恢复")
        else:
            print("   恢复时间: N/A")
        print(f"   消息: {result['message']}")
    except Exception as e:
        print(f"❌ 错误: {e}")


def cpu_stress():
    """CPU 压测"""
    print_header("CPU 压测")

    namespace = input("输入命名空间 [default]: ").strip() or "default"
    pod_name = input("输入 Pod 名称: ").strip()

    if not pod_name:
        print("❌ Pod 名称不能为空")
        return

    cpu_count = input("CPU 核心数 [2]: ").strip() or "2"
    memory_size = input("内存大小 [100Mi, 回车跳过]: ").strip() or None
    duration = input("持续时间 [60s]: ").strip() or "60s"

    confirm = input(f"确认对 {namespace}/{pod_name} 执行 CPU 压测？(yes/no): ").strip().lower()
    if confirm != "yes":
        print("❌ 已取消")
        return

    try:
        injector = ChaosInjector(use_chaos_mesh=True)
        print()
        print("正在注入 CPU 压测故障...")
        result = injector.inject_cpu_stress(
            namespace=namespace,
            pod_name=pod_name,
            cpu_count=int(cpu_count),
            memory_size=memory_size,
            duration=duration
        )

        print()
        if result['success']:
            print("✅ CPU 压测故障注入成功")
            print(f"   故障名称: {result.get('chaos_name', 'N/A')}")
            print(f"   消息: {result['message']}")
            print(f"   故障将在 {duration} 后自动恢复")
            
            # 验证故障是否真正注入成功
            print()
            print("正在验证故障注入状态...")
            verify_result = injector.chaos_mesh.verify_chaos_injection(
                namespace=namespace,
                pod_name=pod_name,
                chaos_name=result.get('chaos_name', ''),
                chaos_type='stress'
            )
            
            print()
            print("【验证结果】")
            print("-" * 60)
            print(f"验证状态: {'✅ 通过' if verify_result['verified'] else '❌ 失败'}")
            print(f"Chaos 状态: {verify_result['details'].get('chaos_phase', 'N/A')}")
            print(f"实验状态: {verify_result['details'].get('experiment_phase', 'N/A')}")
            print(f"Pod 状态: {verify_result['details'].get('pod_status', 'N/A')}")
            print(f"Pod 就绪: {verify_result['details'].get('pod_ready', 'N/A')}")
            print(f"有 Chaos Sidecar: {verify_result['details'].get('has_chaos_sidecar', 'N/A')}")
            
            if verify_result['details'].get('sidecar_names'):
                print(f"Sidecar 容器: {', '.join(verify_result['details']['sidecar_names'])}")
            
            # 显示所有容器名称，便于调试
            if verify_result['details'].get('all_containers'):
                print(f"所有容器: {', '.join(verify_result['details']['all_containers'])}")
            
            if not verify_result['verified']:
                print()
                print("⚠️  故障可能未正确注入，原因：")
                print(f"   {verify_result['details'].get('message', '未知原因')}")
                
                if not verify_result['details'].get('has_chaos_sidecar'):
                    print()
                    print("💡 提示：Pod 可能没有安装 Chaos Mesh sidecar")
                    print("   请检查：")
                    print("   1. Chaos Mesh 是否正确安装")
                    print("   2. Pod 是否在正确的命名空间中")
                    print("   3. 是否需要为 Pod 添加注解以启用 Chaos Mesh")
                    print()
                    print("   例如：kubectl annotate pod <pod-name> chaos-mesh.org/chaos-inject=\"true\"")
                else:
                    print()
                    print("💡 提示：Sidecar 已存在，但 Chaos 资源状态异常")
                    print("   请检查：")
                    print("   1. Chaos Mesh Controller 是否正常运行")
                    print("   2. Chaos 资源是否正确创建")
                    print()
                    print("   查看故障详情：kubectl get stresschaos -n " + namespace)
                    print("   查看故障日志：kubectl logs -n chaos-mesh -l app.kubernetes.io/name=chaos-mesh")
        else:
            print("❌ CPU 压测故障注入失败")
            print(f"   错误: {result['message']}")
    except Exception as e:
        print(f"❌ 错误: {e}")


def network_delay():
    """网络延迟"""
    print_header("网络延迟")

    namespace = input("输入命名空间 [default]: ").strip() or "default"
    pod_name = input("输入 Pod 名称: ").strip()

    if not pod_name:
        print("❌ Pod 名称不能为空")
        return

    latency = input("延迟时间 [100ms]: ").strip() or "100ms"
    jitter = input("抖动时间 [10ms]: ").strip() or "10ms"
    duration = input("持续时间 [60s]: ").strip() or "60s"

    confirm = input(f"确认对 {namespace}/{pod_name} 执行网络延迟？(yes/no): ").strip().lower()
    if confirm != "yes":
        print("❌ 已取消")
        return

    try:
        injector = ChaosInjector(use_chaos_mesh=True)
        print()
        print("正在注入网络延迟故障...")
        result = injector.inject_network_delay(
            namespace=namespace,
            pod_name=pod_name,
            latency=latency,
            jitter=jitter,
            duration=duration
        )

        print()
        if result['success']:
            print("✅ 网络延迟故障注入成功")
            print(f"   故障名称: {result.get('chaos_name', 'N/A')}")
            print(f"   消息: {result['message']}")
            print(f"   故障将在 {duration} 后自动恢复")
        else:
            print("❌ 网络延迟故障注入失败")
            print(f"   错误: {result['message']}")
    except Exception as e:
        print(f"❌ 错误: {e}")


def disk_failure():
    """磁盘故障"""
    print_header("磁盘故障")

    namespace = input("输入命名空间 [default]: ").strip() or "default"
    pod_name = input("输入 Pod 名称: ").strip()

    if not pod_name:
        print("❌ Pod 名称不能为空")
        return

    print("故障类型:")
    print("  1. 磁盘填充（disk_fill）")
    print("  2. 磁盘读错误（disk_read_error）")
    print("  3. 磁盘写错误（disk_write_error）")
    fault_choice = input("选择故障类型 [1]: ").strip() or "1"

    fault_types = {
        "1": "disk_fill",
        "2": "disk_read_error",
        "3": "disk_write_error"
    }
    fault_type = fault_types.get(fault_choice, "disk_fill")

    path = input("目标路径 [/var/log]: ").strip() or "/var/log"
    size = input("填充大小 [1Gi]: ").strip() or "1Gi"
    duration = input("持续时间 [60s]: ").strip() or "60s"

    confirm = input(f"确认对 {namespace}/{pod_name} 执行磁盘故障？(yes/no): ").strip().lower()
    if confirm != "yes":
        print("❌ 已取消")
        return

    try:
        injector = ChaosInjector(use_chaos_mesh=True)
        print()
        print("正在注入磁盘故障...")
        result = injector.inject_disk_failure(
            namespace=namespace,
            pod_name=pod_name,
            path=path,
            fault_type=fault_type,
            size=size,
            duration=duration
        )

        print()
        if result['success']:
            print("✅ 磁盘故障注入成功")
            print(f"   故障名称: {result.get('chaos_name', 'N/A')}")
            print(f"   故障类型: {fault_type}")
            print(f"   消息: {result['message']}")
            print(f"   故障将在 {duration} 后自动恢复")
        else:
            print("❌ 磁盘故障注入失败")
            print(f"   错误: {result['message']}")
    except Exception as e:
        print(f"❌ 错误: {e}")


def query_alerts():
    """查询当前活跃告警"""
    print_header("查询当前活跃告警")

    prometheus_url = input("Prometheus URL [http://localhost:9090]: ").strip() or "http://localhost:9090"

    try:
        checker = MonitorChecker(prometheus_url)
        alerts = checker.prometheus.query_alerts()

        if not alerts:
            print("✓ 当前没有活跃告警")
            return

        print(f"✓ 找到 {len(alerts)} 个活跃告警：")
        print()

        for i, alert in enumerate(alerts, 1):
            labels = alert.get('labels', {})
            annotations = alert.get('annotations', {})

            print(f"【告警 {i}】")
            print(f"  名称: {labels.get('alertname', 'N/A')}")
            print(f"  严重级别: {labels.get('severity', 'N/A')}")
            print(f"  状态: {alert.get('state', 'N/A')}")
            print(f"  描述: {annotations.get('summary', 'N/A')}")
            print()

    except Exception as e:
        print(f"❌ 错误: {e}")
        print("   请确保 Prometheus 正在运行且 URL 正确")


def wait_alert():
    """等待指定告警触发"""
    print_header("等待指定告警触发")

    prometheus_url = input("Prometheus URL [http://localhost:9090]: ").strip() or "http://localhost:9090"
    alert_name = input("告警名称: ").strip()

    if not alert_name:
        print("❌ 告警名称不能为空")
        return

    timeout = input("超时时间（秒）[180]: ").strip() or "180"
    check_interval = input("检查间隔（秒）[10]: ").strip() or "10"

    try:
        checker = MonitorChecker(prometheus_url)
        print()
        print(f"正在等待告警 '{alert_name}' 触发...")
        print(f"超时时间: {timeout} 秒，检查间隔: {check_interval} 秒")
        print("(按 Ctrl+C 可中断)")
        print()

        result = checker.wait_for_alert(
            alert_name=alert_name,
            timeout=int(timeout),
            check_interval=int(check_interval)
        )

        print()
        if result['triggered']:
            print("✅ 告警已触发！")
            print(f"   触发时间: {result['trigger_time']}")
            print(f"   等待时长: {result['wait_time']} 秒")
        else:
            print("❌ 告警未在指定时间内触发")
            print(f"   等待时长: {result['wait_time']} 秒")
            print(f"   消息: {result['message']}")

    except KeyboardInterrupt:
        print()
        print("❌ 已中断")
    except Exception as e:
        print(f"❌ 错误: {e}")


def main():
    """主函数"""
    print()
    print("╔═══════════════════════════════════════════════════════════════════╗")
    print("║           应急演练自动化平台 - 快速交互测试                       ║")
    print("║         Emergency Drill Automation Platform                      ║")
    print("╚═══════════════════════════════════════════════════════════════════╝")
    print()

    while True:
        print_menu()
        choice = input("请输入选项 (0-7): ").strip()

        if choice == "0":
            print()
            print("👋 再见！")
            break
        elif choice == "1":
            list_pods()
        elif choice == "2":
            delete_pod()
        elif choice == "3":
            cpu_stress()
        elif choice == "4":
            network_delay()
        elif choice == "5":
            disk_failure()
        elif choice == "6":
            query_alerts()
        elif choice == "7":
            wait_alert()
        else:
            print("❌ 无效的选项")

        input("\n按 Enter 键继续...")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print()
        print("\n👋 再见！")
