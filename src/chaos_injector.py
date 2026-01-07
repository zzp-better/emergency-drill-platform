"""
故障注入模块 - Chaos Injector

功能：
1. 删除指定的 Pod，模拟应用崩溃
2. 检测 Pod 是否自动恢复
3. 记录恢复时间

作者：应急运维工程师
"""

import time
import logging
from datetime import datetime
from kubernetes import client, config
from kubernetes.client.rest import ApiException

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ChaosInjector:
    """故障注入器"""

    def __init__(self):
        """初始化 Kubernetes 客户端"""
        try:
            # 加载 kubeconfig 配置
            config.load_kube_config()
            self.v1 = client.CoreV1Api()
            self.apps_v1 = client.AppsV1Api()
            logger.info("✓ Kubernetes 客户端初始化成功")
        except Exception as e:
            logger.error(f"✗ Kubernetes 客户端初始化失败: {e}")
            raise

    def delete_pod(self, namespace, pod_name):
        """
        删除指定 Pod，模拟崩溃故障

        参数：
            namespace: 命名空间
            pod_name: Pod 名称

        返回：
            dict: 包含故障注入结果的字典
        """
        result = {
            "scenario": "pod_crash",
            "namespace": namespace,
            "pod_name": pod_name,
            "inject_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "success": False,
            "recovery_time": None,
            "message": ""
        }

        try:
            # 1. 检查 Pod 是否存在
            logger.info(f"检查 Pod 是否存在: {namespace}/{pod_name}")
            pod = self.v1.read_namespaced_pod(name=pod_name, namespace=namespace)
            logger.info(f"✓ Pod 存在，当前状态: {pod.status.phase}")

            # 获取 Pod 的标签（用于后续检测新 Pod）
            labels = pod.metadata.labels

            # 2. 删除 Pod
            logger.info(f"🔥 正在删除 Pod: {namespace}/{pod_name}")
            self.v1.delete_namespaced_pod(
                name=pod_name,
                namespace=namespace,
                body=client.V1DeleteOptions()
            )
            logger.info("✓ Pod 删除请求已发送")
            result["success"] = True
            result["message"] = "Pod 删除成功"

            # 3. 等待 Pod 被删除
            logger.info("等待 Pod 被删除...")
            self._wait_pod_deleted(namespace, pod_name)

            # 4. 检测新 Pod 是否自动创建（如果有 Deployment/ReplicaSet 管理）
            if labels:
                logger.info("检测新 Pod 是否自动创建...")
                recovery_time = self._wait_pod_recovery(namespace, labels)
                result["recovery_time"] = recovery_time
                logger.info(f"✓ Pod 在 {recovery_time} 秒后恢复")

            return result

        except ApiException as e:
            error_msg = f"Kubernetes API 错误: {e.status} - {e.reason}"
            logger.error(f"✗ {error_msg}")
            result["message"] = error_msg
            return result
        except Exception as e:
            error_msg = f"未知错误: {str(e)}"
            logger.error(f"✗ {error_msg}")
            result["message"] = error_msg
            return result

    def _wait_pod_deleted(self, namespace, pod_name, timeout=60):
        """等待 Pod 被删除"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                self.v1.read_namespaced_pod(name=pod_name, namespace=namespace)
                time.sleep(2)
            except ApiException as e:
                if e.status == 404:
                    logger.info("✓ Pod 已被删除")
                    return
                raise
        logger.warning(f"⚠ Pod 删除超时（{timeout}秒）")

    def _wait_pod_recovery(self, namespace, labels, timeout=120):
        """
        等待新 Pod 创建并变为 Running 状态

        返回：
            int: 恢复时间（秒）
        """
        start_time = time.time()
        label_selector = ",".join([f"{k}={v}" for k, v in labels.items()])

        while time.time() - start_time < timeout:
            try:
                pods = self.v1.list_namespaced_pod(
                    namespace=namespace,
                    label_selector=label_selector
                )

                for pod in pods.items:
                    if pod.status.phase == "Running":
                        # 检查容器是否真正就绪
                        if pod.status.container_statuses:
                            all_ready = all(
                                cs.ready for cs in pod.status.container_statuses
                            )
                            if all_ready:
                                recovery_time = int(time.time() - start_time)
                                return recovery_time

                time.sleep(3)
            except Exception as e:
                logger.error(f"检测 Pod 恢复时出错: {e}")
                time.sleep(3)

        logger.warning(f"⚠ Pod 恢复超时（{timeout}秒）")
        return int(time.time() - start_time)

    def list_pods(self, namespace):
        """
        列出指定命名空间的所有 Pod

        参数：
            namespace: 命名空间

        返回：
            list: Pod 列表
        """
        try:
            pods = self.v1.list_namespaced_pod(namespace=namespace)
            pod_list = []
            for pod in pods.items:
                pod_list.append({
                    "name": pod.metadata.name,
                    "status": pod.status.phase,
                    "node": pod.spec.node_name,
                    "created": pod.metadata.creation_timestamp
                })
            return pod_list
        except Exception as e:
            logger.error(f"获取 Pod 列表失败: {e}")
            return []


def main():
    """主函数 - 用于测试"""
    print("=" * 60)
    print("应急演练自动化平台 - 故障注入模块")
    print("=" * 60)
    print()

    # 初始化故障注入器
    injector = ChaosInjector()

    # 示例：列出 default 命名空间的 Pod
    print("【示例 1】列出 default 命名空间的所有 Pod：")
    print("-" * 60)
    pods = injector.list_pods("default")
    if pods:
        for pod in pods:
            print(f"  Pod: {pod['name']}")
            print(f"  状态: {pod['status']}")
            print(f"  节点: {pod['node']}")
            print()
    else:
        print("  没有找到 Pod")

    print()
    print("【使用说明】")
    print("-" * 60)
    print("要删除一个 Pod，请使用以下代码：")
    print()
    print("  injector = ChaosInjector()")
    print("  result = injector.delete_pod('namespace', 'pod-name')")
    print("  print(result)")
    print()
    print("【下一步】")
    print("-" * 60)
    print("1. 确保有一个运行中的 Kubernetes 集群")
    print("2. 部署一个测试应用（如 nginx）")
    print("3. 使用 delete_pod() 方法删除 Pod")
    print("4. 观察 Pod 是否自动恢复")
    print()


if __name__ == "__main__":
    main()
