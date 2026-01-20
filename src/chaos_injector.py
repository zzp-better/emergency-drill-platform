"""
故障注入模块 - Chaos Injector

功能：
1. 删除指定的 Pod，模拟应用崩溃
2. 检测 Pod 是否自动恢复
3. 记录恢复时间
4. 集成 Chaos Mesh 支持更多故障场景

作者：应急运维工程师
"""

import time
import logging
import yaml
from datetime import datetime
from typing import Dict, Optional
from kubernetes import client, config
from kubernetes.client.rest import ApiException

# 导入 Chaos Mesh 注入器
try:
    from chaos_mesh_injector import ChaosMeshInjector
    CHAOS_MESH_AVAILABLE = True
except ImportError:
    CHAOS_MESH_AVAILABLE = False
    logging.warning("Chaos Mesh 注入器未安装，仅支持原生 Kubernetes 故障注入")

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ChaosInjector:
    """故障注入器 - 统一接口，支持原生 K8s 和 Chaos Mesh"""

    def __init__(self, use_chaos_mesh: bool = False):
        """
        初始化故障注入器

        参数：
            use_chaos_mesh: 是否使用 Chaos Mesh（默认 False）
        """
        self.use_chaos_mesh = use_chaos_mesh
        
        try:
            # 加载 kubeconfig 配置
            config.load_kube_config()
            self.v1 = client.CoreV1Api()
            self.apps_v1 = client.AppsV1Api()
            logger.info("✓ Kubernetes 客户端初始化成功")
        except Exception as e:
            logger.error(f"✗ Kubernetes 客户端初始化失败: {e}")
            raise

        # 初始化 Chaos Mesh 注入器（如果需要）
        if use_chaos_mesh:
            if CHAOS_MESH_AVAILABLE:
                try:
                    self.chaos_mesh = ChaosMeshInjector()
                    logger.info("✓ Chaos Mesh 注入器初始化成功")
                except Exception as e:
                    logger.error(f"✗ Chaos Mesh 注入器初始化失败: {e}")
                    logger.warning("将回退到原生 Kubernetes 故障注入")
                    self.use_chaos_mesh = False
            else:
                logger.warning("Chaos Mesh 注入器不可用，将使用原生 Kubernetes 故障注入")
                self.use_chaos_mesh = False

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

    def inject_cpu_stress(self, namespace: str, pod_name: str, 
                         cpu_count: Optional[int] = None,
                         memory_size: Optional[str] = None,
                         duration: str = "60s") -> Dict:
        """
        注入 CPU/内存压测故障

        参数：
            namespace: 命名空间
            pod_name: 目标 Pod 名称
            cpu_count: CPU 核心数
            memory_size: 内存大小（如 100Mi, 1Gi，会自动转换为字节数）
            duration: 持续时间

        返回：
            dict: 故障注入结果
        """
        if not self.use_chaos_mesh:
            logger.error("CPU 压测需要 Chaos Mesh，请初始化时设置 use_chaos_mesh=True")
            return {
                "scenario": "cpu_stress",
                "success": False,
                "message": "CPU 压测需要 Chaos Mesh"
            }

        # 修复内存大小格式：Chaos Mesh StressChaos 期望的字节格式（不带单位）
        if memory_size:
            # 支持的输入格式：100Mi, 100mi, 100MB, 100mb, 100, 104857600
            memory_size = memory_size.lower()
            
            # 转换为字节数
            if memory_size.endswith('mi') or memory_size.endswith('mb'):
                # Mebibyte/Megabyte -> 字节 (1 Mi = 1024 * 1024 = 1048576 bytes)
                num = int(memory_size[:-2])
                memory_size = str(num * 1024 * 1024)
            elif memory_size.endswith('gi') or memory_size.endswith('gb'):
                # Gibibyte/Gigabyte -> 字节 (1 Gi = 1024 * 1024 * 1024 = 1073741824 bytes)
                num = int(memory_size[:-2])
                memory_size = str(num * 1024 * 1024 * 1024)
            elif memory_size.endswith('ki') or memory_size.endswith('kb'):
                # Kibibyte/Kilobyte -> 字节 (1 Ki = 1024 bytes)
                num = int(memory_size[:-2])
                memory_size = str(num * 1024)
            # 如果是纯数字，假设已经是字节数

        return self.chaos_mesh.create_stress_chaos(
            namespace=namespace,
            pod_name=pod_name,
            cpu_count=cpu_count,
            memory_size=memory_size,
            duration=duration
        )

    def inject_network_delay(self, namespace: str, pod_name: str,
                            latency: str = "100ms",
                            jitter: str = "10ms",
                            duration: str = "60s") -> Dict:
        """
        注入网络延迟故障

        参数：
            namespace: 命名空间
            pod_name: 目标 Pod 名称
            latency: 延迟时间
            jitter: 抖动时间
            duration: 持续时间

        返回：
            dict: 故障注入结果
        """
        if not self.use_chaos_mesh:
            logger.error("网络延迟需要 Chaos Mesh，请初始化时设置 use_chaos_mesh=True")
            return {
                "scenario": "network_delay",
                "success": False,
                "message": "网络延迟需要 Chaos Mesh"
            }

        return self.chaos_mesh.create_network_delay(
            namespace=namespace,
            pod_name=pod_name,
            latency=latency,
            jitter=jitter,
            duration=duration
        )

    def inject_disk_failure(self, namespace: str, pod_name: str,
                           path: str = "/var/log",
                           fault_type: str = "disk_fill",
                           size: str = "1Gi",
                           duration: str = "60s") -> Dict:
        """
        注入磁盘故障

        参数：
            namespace: 命名空间
            pod_name: 目标 Pod 名称
            path: 目标路径
            fault_type: 故障类型
            size: 填充大小
            duration: 持续时间

        返回：
            dict: 故障注入结果
        """
        if not self.use_chaos_mesh:
            logger.error("磁盘故障需要 Chaos Mesh，请初始化时设置 use_chaos_mesh=True")
            return {
                "scenario": "disk_failure",
                "success": False,
                "message": "磁盘故障需要 Chaos Mesh"
            }

        return self.chaos_mesh.create_disk_failure(
            namespace=namespace,
            pod_name=pod_name,
            path=path,
            fault_type=fault_type,
            size=size,
            duration=duration
        )

    def load_scenario_config(self, config_path: str) -> Dict:
        """
        加载场景配置文件

        参数：
            config_path: 配置文件路径

        返回：
            dict: 配置内容
        """
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            logger.info(f"✓ 配置文件加载成功: {config_path}")
            return config
        except Exception as e:
            logger.error(f"✗ 配置文件加载失败: {e}")
            return {}

    def inject_from_config(self, config_path: str) -> Dict:
        """
        根据配置文件注入故障

        参数：
            config_path: 配置文件路径

        返回：
            dict: 故障注入结果
        """
        config = self.load_scenario_config(config_path)
        if not config:
            return {
                "success": False,
                "message": "配置文件加载失败"
            }

        scenario = config.get('scenario', {})
        target = config.get('target', {})
        fault = config.get('fault', {})

        scenario_type = scenario.get('type')
        namespace = target.get('namespace')
        pod_name = target.get('pod_name')

        logger.info(f"开始执行演练场景: {scenario.get('name')}")
        logger.info(f"场景类型: {scenario_type}")

        # 根据场景类型执行不同的故障注入
        if scenario_type == 'pod_crash':
            return self.delete_pod(namespace, pod_name)
        elif scenario_type == 'cpu_stress':
            cpu_config = fault.get('cpu', {})
            memory_config = fault.get('memory', {})
            return self.inject_cpu_stress(
                namespace=namespace,
                pod_name=pod_name,
                cpu_count=cpu_config.get('workers'),
                memory_size=memory_config.get('size') if memory_config.get('enabled') else None,
                duration=fault.get('duration', '60s')
            )
        elif scenario_type == 'network_delay':
            network_config = fault.get('network', {})
            return self.inject_network_delay(
                namespace=namespace,
                pod_name=pod_name,
                latency=network_config.get('latency', '100ms'),
                jitter=network_config.get('jitter', '10ms'),
                duration=fault.get('duration', '60s')
            )
        elif scenario_type == 'disk_io':
            fault_type = fault.get('fault_type', 'disk_fill')
            if fault_type == 'disk_fill':
                fill_config = fault.get('fill', {})
                return self.inject_disk_failure(
                    namespace=namespace,
                    pod_name=pod_name,
                    path=fill_config.get('path', '/var/log'),
                    fault_type=fault_type,
                    size=fill_config.get('size', '1Gi'),
                    duration=fault.get('duration', '60s')
                )
            else:
                return self.inject_disk_failure(
                    namespace=namespace,
                    pod_name=pod_name,
                    fault_type=fault_type,
                    duration=fault.get('duration', '60s')
                )
        else:
            logger.error(f"未知的场景类型: {scenario_type}")
            return {
                "success": False,
                "message": f"未知的场景类型: {scenario_type}"
            }


def main():
    """主函数 - 用于测试"""
    print("=" * 70)
    print("应急演练自动化平台 - 故障注入模块")
    print("=" * 70)
    print()

    # 检查是否使用 Chaos Mesh
    use_chaos_mesh = False
    if CHAOS_MESH_AVAILABLE:
        use_chaos = input("是否使用 Chaos Mesh？(yes/no) [no]: ").strip().lower()
        use_chaos_mesh = use_chaos == "yes"

    # 初始化故障注入器
    injector = ChaosInjector(use_chaos_mesh=use_chaos_mesh)

    # 示例：列出 default 命名空间的 Pod
    print("【示例 1】列出 default 命名空间的所有 Pod：")
    print("-" * 70)
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
    print("-" * 70)

    if use_chaos_mesh:
        print("Chaos Mesh 模式已启用，支持以下故障注入：")
        print()
        print("1. Pod 崩溃（原生 K8s）:")
        print("   injector.delete_pod('namespace', 'pod-name')")
        print()
        print("2. CPU/内存压测:")
        print("   injector.inject_cpu_stress('namespace', 'pod-name', cpu_count=2, memory_size='100Mi')")
        print()
        print("3. 网络延迟:")
        print("   injector.inject_network_delay('namespace', 'pod-name', latency='100ms')")
        print()
        print("4. 磁盘故障:")
        print("   injector.inject_disk_failure('namespace', 'pod-name', fault_type='disk_fill')")
        print()
        print("5. 从配置文件注入:")
        print("   injector.inject_from_config('scenarios/cpu_stress.yaml')")
        print()
    else:
        print("原生 Kubernetes 模式，支持以下故障注入：")
        print()
        print("1. Pod 崩溃:")
        print("   injector.delete_pod('namespace', 'pod-name')")
        print()
        print("2. 从配置文件注入:")
        print("   injector.inject_from_config('scenarios/pod_crash.yaml')")
        print()

    print("【下一步】")
    print("-" * 70)
    print("1. 确保有一个运行中的 Kubernetes 集群")
    print("2. 如需使用 Chaos Mesh，请先安装 Chaos Mesh")
    print("3. 部署一个测试应用（如 nginx）")
    print("4. 使用相应的方法注入故障")
    print("5. 观察 Pod 是否自动恢复")
    print()


if __name__ == "__main__":
    main()
