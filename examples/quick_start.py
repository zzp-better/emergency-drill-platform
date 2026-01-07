"""
故障注入示例 - 快速开始

这个示例展示如何使用 ChaosInjector 删除 Pod

使用前提：
1. 有一个运行中的 Kubernetes 集群
2. kubectl 已经配置好
3. 至少有一个运行中的 Pod
"""

import sys
import os

# 添加 src 目录到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from chaos_injector import ChaosInjector


def example_list_pods():
    """示例 1：列出所有 Pod"""
    print("=" * 70)
    print("示例 1：列出命名空间中的所有 Pod")
    print("=" * 70)
    print()

    injector = ChaosInjector()

    # 列出 default 命名空间的 Pod
    namespace = "default"
    print(f"正在获取 {namespace} 命名空间的 Pod...")
    print()

    pods = injector.list_pods(namespace)

    if pods:
        print(f"找到 {len(pods)} 个 Pod：")
        print()
        for i, pod in enumerate(pods, 1):
            print(f"{i}. Pod 名称: {pod['name']}")
            print(f"   状态: {pod['status']}")
            print(f"   节点: {pod['node']}")
            print(f"   创建时间: {pod['created']}")
            print()
    else:
        print(f"在 {namespace} 命名空间中没有找到 Pod")
        print()
        print("提示：")
        print("1. 请确保 Kubernetes 集群正在运行")
        print("2. 尝试部署一个测试应用：")
        print("   kubectl create deployment nginx --image=nginx")
        print("   kubectl scale deployment nginx --replicas=3")


def example_delete_pod():
    """示例 2：删除指定 Pod"""
    print()
    print("=" * 70)
    print("示例 2：删除 Pod（故障注入）")
    print("=" * 70)
    print()

    injector = ChaosInjector()

    # 提示用户输入
    print("请提供要删除的 Pod 信息：")
    namespace = input("命名空间 [default]: ").strip() or "default"
    pod_name = input("Pod 名称: ").strip()

    if not pod_name:
        print("错误：Pod 名称不能为空")
        return

    print()
    print(f"将要删除: {namespace}/{pod_name}")
    confirm = input("确认执行？(yes/no): ").strip().lower()

    if confirm != "yes":
        print("操作已取消")
        return

    print()
    print("开始执行故障注入...")
    print("-" * 70)

    result = injector.delete_pod(namespace, pod_name)

    print()
    print("=" * 70)
    print("故障注入结果")
    print("=" * 70)
    print()
    print(f"场景: {result['scenario']}")
    print(f"命名空间: {result['namespace']}")
    print(f"Pod 名称: {result['pod_name']}")
    print(f"注入时间: {result['inject_time']}")
    print(f"执行状态: {'成功' if result['success'] else '失败'}")

    if result['recovery_time']:
        print(f"恢复时间: {result['recovery_time']} 秒")
    else:
        print(f"恢复时间: 未检测到（Pod 可能没有自动重建）")

    print(f"消息: {result['message']}")
    print()


def main():
    """主函数"""
    print()
    print("╔═══════════════════════════════════════════════════════════════════╗")
    print("║         应急演练自动化平台 - 故障注入示例                          ║")
    print("║                Emergency Drill Platform                           ║")
    print("╚═══════════════════════════════════════════════════════════════════╝")
    print()

    while True:
        print("请选择示例：")
        print("  1. 列出所有 Pod")
        print("  2. 删除指定 Pod（故障注入）")
        print("  0. 退出")
        print()

        choice = input("请输入选项 [0-2]: ").strip()

        if choice == "1":
            example_list_pods()
        elif choice == "2":
            example_delete_pod()
        elif choice == "0":
            print()
            print("感谢使用！")
            break
        else:
            print("无效选项，请重新选择")

        print()
        input("按回车键继续...")
        print("\n" * 2)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n操作已取消")
    except Exception as e:
        print(f"\n错误: {e}")
