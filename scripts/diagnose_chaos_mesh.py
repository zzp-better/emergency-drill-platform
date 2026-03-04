#!/usr/bin/env python3
"""
Chaos Mesh 诊断脚本

用于诊断 Chaos Mesh sidecar 注入问题
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from kubernetes import client, config
from kubernetes.client.rest import ApiException


def print_section(title):
    """打印章节标题"""
    print()
    print("=" * 70)
    print(f"  {title}")
    print("=" * 70)
    print()


def check_chaos_mesh_installation():
    """检查 Chaos Mesh 是否安装"""
    print_section("1. 检查 Chaos Mesh 安装")

    try:
        config.load_kube_config()
        v1 = client.CoreV1Api()
        custom_api = client.CustomObjectsApi()

        # 检查 chaos-mesh 命名空间
        try:
            ns = v1.read_namespace(name="chaos-mesh")
            print(f"✅ Chaos Mesh 命名空间存在: {ns.metadata.name}")
        except ApiException as e:
            if e.status == 404:
                print("❌ Chaos Mesh 命名空间不存在")
                print("   请先安装 Chaos Mesh:")
                print("   helm repo add chaos-mesh https://charts.chaos-mesh.org")
                print("   helm install chaos-mesh chaos-mesh/chaos-mesh -n chaos-mesh")
                return False
            raise

        # 检查 Chaos Mesh Pod
        try:
            pods = v1.list_namespaced_pod(namespace="chaos-mesh")
            print(f"✅ Chaos Mesh Pod 数量: {len(pods.items)}")
            for pod in pods.items:
                print(f"   - {pod.metadata.name} ({pod.status.phase})")
        except Exception as e:
            print(f"❌ 无法获取 Chaos Mesh Pod: {e}")
            return False

        # 检查 Chaos Mesh CRD
        try:
            apiextensions = client.ApiextensionsV1Api()
            crds = apiextensions.list_custom_resource_definition()
            chaos_crds = [crd for crd in crds.items if 'chaos-mesh.org' in crd.spec.group]
            print(f"✅ Chaos Mesh CRD 数量: {len(chaos_crds)}")
            for crd in chaos_crds[:5]:  # 只显示前5个
                print(f"   - {crd.metadata.name}")
        except Exception as e:
            print(f"❌ 无法获取 Chaos Mesh CRD: {e}")
            return False

        return True

    except Exception as e:
        print(f"❌ 检查 Chaos Mesh 安装失败: {e}")
        return False


def check_pod_sidecar(pod_name, namespace="default"):
    """检查 Pod 是否有 Chaos Mesh sidecar"""
    print_section(f"2. 检查 Pod: {namespace}/{pod_name}")

    try:
        config.load_kube_config()
        v1 = client.CoreV1Api()

        # 获取 Pod
        pod = v1.read_namespaced_pod(name=pod_name, namespace=namespace)

        print(f"✅ Pod 状态: {pod.status.phase}")
        print(f"✅ Pod 就绪: {all(cs.ready for cs in pod.status.container_statuses or [])}")

        # 检查注解
        annotations = pod.metadata.annotations or {}
        print(f"\n📋 Pod 注解:")
        if annotations:
            for key, value in annotations.items():
                print(f"   {key}: {value}")
        else:
            print("   (无注解)")

        # 检查是否有 Chaos Mesh 注解
        chaos_inject = annotations.get("chaos-mesh.org/chaos-inject")
        if chaos_inject == "true":
            print(f"\n✅ Pod 已启用 Chaos Mesh 注入")
        else:
            print(f"\n⚠️  Pod 未启用 Chaos Mesh 注入")
            print(f"   chaos-mesh.org/chaos-inject: {chaos_inject or '(未设置)'}")
            print(f"\n💡 解决方法:")
            print(f"   kubectl annotate pod {pod_name} chaos-mesh.org/chaos-inject=\"true\" -n {namespace}")
            print(f"   或者为 Deployment 添加注解:")
            print(f"   kubectl annotate deployment <deployment-name> chaos-mesh.org/chaos-inject=\"true\" -n {namespace}")

        # 检查容器
        containers = pod.spec.containers or []
        print(f"\n📦 容器列表 ({len(containers)} 个):")
        for i, c in enumerate(containers, 1):
            print(f"   {i}. {c.name}")
            print(f"      镜像: {c.image}")

        # 检查 sidecar
        sidecar_keywords = ['chaos', 'bypass', 'sidecar']
        sidecar_names = [c.name for c in containers if any(kw in c.name.lower() for kw in sidecar_keywords)]

        if sidecar_names:
            print(f"\n✅ 检测到 Chaos Mesh sidecar: {', '.join(sidecar_names)}")
            return True
        else:
            print(f"\n❌ 未检测到 Chaos Mesh sidecar")
            print(f"\n💡 可能的原因:")
            print(f"   1. Pod 缺少 chaos-mesh.org/chaos-inject 注解")
            print(f"   2. Pod 创建时 Chaos Mesh 未安装")
            print(f"   3. Pod 所在命名空间未启用自动注入")
            print(f"\n💡 解决方法:")
            print(f"   方法 1: 为现有 Pod 添加注解（临时）")
            print(f"   kubectl annotate pod {pod_name} chaos-mesh.org/chaos-inject=\"true\" -n {namespace}")
            print(f"   方法 2: 删除 Pod 重新创建（推荐）")
            print(f"   kubectl delete pod {pod_name} -n {namespace}")
            print(f"   方法 3: 为 Deployment 添加注解（永久）")
            print(f"   kubectl annotate deployment <deployment-name> chaos-mesh.org/chaos-inject=\"true\" -n {namespace}")
            print(f"   kubectl delete pod -l app=<app-label> -n {namespace}")
            return False

    except ApiException as e:
        if e.status == 404:
            print(f"❌ Pod 不存在: {namespace}/{pod_name}")
        else:
            print(f"❌ 获取 Pod 失败: {e}")
        return False
    except Exception as e:
        print(f"❌ 检查 Pod 失败: {e}")
        return False


def check_namespace_injection(namespace="default"):
    """检查命名空间是否启用自动注入"""
    print_section(f"3. 检查命名空间: {namespace}")

    try:
        config.load_kube_config()
        v1 = client.CoreV1Api()

        ns = v1.read_namespace(name=namespace)
        annotations = ns.metadata.annotations or {}

        print(f"📋 命名空间注解:")
        if annotations:
            for key, value in annotations.items():
                print(f"   {key}: {value}")
        else:
            print("   (无注解)")

        chaos_inject = annotations.get("chaos-mesh.org/chaos-inject")
        if chaos_inject == "true":
            print(f"\n✅ 命名空间已启用 Chaos Mesh 自动注入")
        else:
            print(f"\n⚠️  命名空间未启用 Chaos Mesh 自动注入")
            print(f"   chaos-mesh.org/chaos-inject: {chaos_inject or '(未设置)'}")
            print(f"\n💡 为命名空间启用自动注入:")
            print(f"   kubectl annotate namespace {namespace} chaos-mesh.org/chaos-inject=\"true\"")

    except ApiException as e:
        if e.status == 404:
            print(f"❌ 命名空间不存在: {namespace}")
        else:
            print(f"❌ 获取命名空间失败: {e}")
    except Exception as e:
        print(f"❌ 检查命名空间失败: {e}")


def main():
    """主函数"""
    print()
    print("╔═══════════════════════════════════════════════════════════════════╗")
    print("║           Chaos Mesh Sidecar 诊断工具                              ║")
    print("╚═══════════════════════════════════════════════════════════════════╝")

    # 获取参数
    if len(sys.argv) < 2:
        print("\n用法: python diagnose_chaos_mesh.py <pod-name> [namespace]")
        print("\n示例:")
        print("  python diagnose_chaos_mesh.py nginx-test-d8c46d48d-z4ktd")
        print("  python diagnose_chaos_mesh.py nginx-test-d8c46d48d-z4ktd default")
        sys.exit(1)

    pod_name = sys.argv[1]
    namespace = sys.argv[2] if len(sys.argv) > 2 else "default"

    # 1. 检查 Chaos Mesh 安装
    chaos_installed = check_chaos_mesh_installation()
    if not chaos_installed:
        print("\n❌ Chaos Mesh 未安装，请先安装 Chaos Mesh")
        sys.exit(1)

    # 2. 检查 Pod sidecar
    has_sidecar = check_pod_sidecar(pod_name, namespace)

    # 3. 检查命名空间
    check_namespace_injection(namespace)

    # 总结
    print_section("诊断总结")
    if has_sidecar:
        print("✅ Pod 已有 Chaos Mesh sidecar")
        print("   可以正常使用 Chaos Mesh 故障注入功能")
    else:
        print("❌ Pod 缺少 Chaos Mesh sidecar")
        print("   请按照上述方法为 Pod 添加 sidecar")
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ 操作已取消")
    except Exception as e:
        print(f"\n\n❌ 发生错误: {e}")
        import traceback
        traceback.print_exc()
