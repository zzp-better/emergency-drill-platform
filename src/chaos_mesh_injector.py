"""
Chaos Mesh 故障注入模块 - Chaos Mesh Injector

功能：
1. 通过 Chaos Mesh API 注入多种故障场景
2. 支持 CPU 压测、内存压测、网络延迟、磁盘 IO 故障等
3. 自动管理故障的生命周期（创建、暂停、恢复、删除）
4. 记录故障注入和恢复时间

作者：应急运维工程师
"""

import time
import logging
import yaml
from datetime import datetime
from typing import Dict, List, Optional
from kubernetes import client, config
from kubernetes.client.rest import ApiException

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ChaosMeshInjector:
    """Chaos Mesh 故障注入器"""

    def __init__(self):
        """初始化 Kubernetes 客户端"""
        try:
            # 加载 kubeconfig 配置
            config.load_kube_config()
            self.v1 = client.CoreV1Api()
            self.custom_api = client.CustomObjectsApi()
            logger.info("✓ Chaos Mesh 客户端初始化成功")
        except Exception as e:
            logger.error(f"✗ Chaos Mesh 客户端初始化失败: {e}")
            raise

    def create_stress_chaos(self, namespace: str, pod_name: str, 
                          cpu_count: Optional[int] = None,
                          memory_size: Optional[str] = None,
                          duration: str = "60s") -> Dict:
        """
        创建 CPU/内存压测故障

        参数：
            namespace: 命名空间
            pod_name: 目标 Pod 名称
            cpu_count: CPU 核心数（如 2）
            memory_size: 内存大小（如 100Mi, 1Gi，会自动转换为字节数）
            duration: 持续时间（如 60s, 5m）

        返回：
            dict: 故障注入结果
        """
        chaos_name = f"stress-{pod_name}-{int(time.time())}"

        spec = {
            "mode": "one",
            "selector": {
                "namespaces": [namespace],
                "pods": {
                    namespace: [pod_name]
                }
            },
            "duration": duration,
            "stressors": {}
        }

        if cpu_count:
            spec["stressors"]["cpu"] = {
                "workers": cpu_count,
                "load": 100
            }

        if memory_size:
            # Chaos Mesh StressChaos 期望的字节格式（不带单位）
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
            
            spec["stressors"]["memory"] = {
                "workers": 1,
                "size": memory_size
            }

        result = self._create_chaos(
            group="chaos-mesh.org",
            version="v1alpha1",
            plural="stresschaos",
            namespace=namespace,
            name=chaos_name,
            spec=spec,
            chaos_type="stress"
        )

        return result

    def create_network_delay(self, namespace: str, pod_name: str,
                            latency: str = "100ms",
                            jitter: str = "10ms",
                            duration: str = "60s") -> Dict:
        """
        创建网络延迟故障

        参数：
            namespace: 命名空间
            pod_name: 目标 Pod 名称
            latency: 延迟时间（如 100ms, 1s）
            jitter: 抖动时间（如 10ms）
            duration: 持续时间

        返回：
            dict: 故障注入结果
        """
        chaos_name = f"network-delay-{pod_name}-{int(time.time())}"

        spec = {
            "mode": "one",
            "selector": {
                "namespaces": [namespace],
                "pods": {
                    namespace: [pod_name]
                }
            },
            "duration": duration,
            "direction": "to",
            "delay": {
                "latency": latency,
                "jitter": jitter
            }
        }

        result = self._create_chaos(
            group="chaos-mesh.org",
            version="v1alpha1",
            plural="networkchaos",
            namespace=namespace,
            name=chaos_name,
            spec=spec,
            chaos_type="network_delay"
        )

        return result

    def create_network_loss(self, namespace: str, pod_name: str,
                           loss: str = "50%",
                           correlation: str = "0",
                           duration: str = "60s") -> Dict:
        """
        创建网络丢包故障

        参数：
            namespace: 命名空间
            pod_name: 目标 Pod 名称
            loss: 丢包率（如 50%, 100%）
            correlation: 相关性（0-1）
            duration: 持续时间

        返回：
            dict: 故障注入结果
        """
        chaos_name = f"network-loss-{pod_name}-{int(time.time())}"

        spec = {
            "mode": "one",
            "selector": {
                "namespaces": [namespace],
                "pods": {
                    namespace: [pod_name]
                }
            },
            "duration": duration,
            "direction": "to",
            "loss": {
                "loss": loss,
                "correlation": correlation
            }
        }

        result = self._create_chaos(
            group="chaos-mesh.org",
            version="v1alpha1",
            plural="networkchaos",
            namespace=namespace,
            name=chaos_name,
            spec=spec,
            chaos_type="network_loss"
        )

        return result

    def create_disk_failure(self, namespace: str, pod_name: str,
                           path: str = "/var/log",
                           fault_type: str = "disk_fill",
                           size: str = "1Gi",
                           duration: str = "60s") -> Dict:
        """
        创建磁盘故障

        参数：
            namespace: 命名空间
            pod_name: 目标 Pod 名称
            path: 目标路径
            fault_type: 故障类型（disk_fill, disk_read_error, disk_write_error）
            size: 填充大小（disk_fill 时使用）
            duration: 持续时间

        返回：
            dict: 故障注入结果
        """
        chaos_name = f"io-{pod_name}-{int(time.time())}"

        spec = {
            "mode": "one",
            "selector": {
                "namespaces": [namespace],
                "pods": {
                    namespace: [pod_name]
                }
            },
            "duration": duration,
            "volumePath": path
        }

        if fault_type == "disk_fill":
            spec["fillOptions"] = {
                "fillSize": size
            }
        elif fault_type == "disk_read_error":
            spec["readError"] = True
        elif fault_type == "disk_write_error":
            spec["writeError"] = True

        result = self._create_chaos(
            group="chaos-mesh.org",
            version="v1alpha1",
            plural="iochaos",
            namespace=namespace,
            name=chaos_name,
            spec=spec,
            chaos_type="io"
        )

        return result

    def create_pod_kill(self, namespace: str, pod_name: str,
                       grace_period: int = 0) -> Dict:
        """
        创建 Pod 杀死故障（类似 Pod 崩溃）

        参数：
            namespace: 命名空间
            pod_name: 目标 Pod 名称
            grace_period: 优雅终止时间（秒）

        返回：
            dict: 故障注入结果
        """
        chaos_name = f"pod-kill-{pod_name}-{int(time.time())}"

        spec = {
            "mode": "one",
            "selector": {
                "namespaces": [namespace],
                "pods": {
                    namespace: [pod_name]
                }
            },
            "gracePeriodSeconds": grace_period
        }

        result = self._create_chaos(
            group="chaos-mesh.org",
            version="v1alpha1",
            plural="podchaos",
            namespace=namespace,
            name=chaos_name,
            spec=spec,
            chaos_type="pod_kill"
        )

        return result

    def _create_chaos(self, group: str, version: str, plural: str,
                     namespace: str, name: str, spec: Dict,
                     chaos_type: str) -> Dict:
        """
        创建 Chaos Mesh 故障的通用方法

        参数：
            group: API 组
            version: API 版本
            plural: 资源复数形式
            namespace: 命名空间
            name: 故障名称
            spec: 故障规格
            chaos_type: 故障类型

        返回：
            dict: 故障注入结果
        """
        result = {
            "chaos_type": chaos_type,
            "chaos_name": name,
            "namespace": namespace,
            "inject_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "success": False,
            "message": ""
        }

        try:
            # 构建 Chaos Mesh 资源
            chaos_manifest = {
                "apiVersion": f"{group}/{version}",
                "kind": plural.capitalize()[:-1],  # stresschaos -> StressChaos
                "metadata": {
                    "name": name,
                    "namespace": namespace
                },
                "spec": spec
            }

            logger.info(f"正在创建 {chaos_type} 故障: {name}")
            logger.debug(f"故障配置: {chaos_manifest}")

            # 创建 Chaos Mesh 资源
            self.custom_api.create_namespaced_custom_object(
                group=group,
                version=version,
                namespace=namespace,
                plural=plural,
                body=chaos_manifest
            )

            logger.info(f"✓ {chaos_type} 故障创建成功")
            result["success"] = True
            result["message"] = f"{chaos_type} 故障创建成功"

            return result

        except ApiException as e:
            error_msg = f"Kubernetes API 错误: {e.status} - {e.reason}"
            if e.body:
                try:
                    body = yaml.safe_load(e.body)
                    if 'message' in body:
                        error_msg += f" - {body['message']}"
                except:
                    pass
            logger.error(f"✗ {error_msg}")
            result["message"] = error_msg
            return result

        except Exception as e:
            error_msg = f"未知错误: {str(e)}"
            logger.error(f"✗ {error_msg}")
            result["message"] = error_msg
            return result

    def delete_chaos(self, namespace: str, chaos_name: str, chaos_type: str) -> bool:
        """
        删除 Chaos Mesh 故障

        参数：
            namespace: 命名空间
            chaos_name: 故障名称
            chaos_type: 故障类型

        返回：
            bool: 是否删除成功
        """
        chaos_map = {
            "stress": ("chaos-mesh.org", "v1alpha1", "stresschaos"),
            "network_delay": ("chaos-mesh.org", "v1alpha1", "networkchaos"),
            "network_loss": ("chaos-mesh.org", "v1alpha1", "networkchaos"),
            "io": ("chaos-mesh.org", "v1alpha1", "iochaos"),
            "pod_kill": ("chaos-mesh.org", "v1alpha1", "podchaos")
        }

        if chaos_type not in chaos_map:
            logger.error(f"未知的故障类型: {chaos_type}")
            return False

        group, version, plural = chaos_map[chaos_type]

        try:
            logger.info(f"正在删除故障: {chaos_name}")
            self.custom_api.delete_namespaced_custom_object(
                group=group,
                version=version,
                namespace=namespace,
                plural=plural,
                name=chaos_name
            )
            logger.info(f"✓ 故障删除成功: {chaos_name}")
            return True

        except ApiException as e:
            if e.status == 404:
                logger.warning(f"⚠ 故障不存在: {chaos_name}")
                return True
            logger.error(f"✗ 删除故障失败: {e}")
            return False

        except Exception as e:
            logger.error(f"✗ 删除故障失败: {e}")
            return False

    def list_chaos(self, namespace: str, chaos_type: Optional[str] = None) -> List[Dict]:
        """
        列出指定命名空间的故障

        参数：
            namespace: 命名空间
            chaos_type: 故障类型（可选）

        返回：
            list: 故障列表
        """
        chaos_map = {
            "stress": ("chaos-mesh.org", "v1alpha1", "stresschaos"),
            "network": ("chaos-mesh.org", "v1alpha1", "networkchaos"),
            "io": ("chaos-mesh.org", "v1alpha1", "iochaos"),
            "pod": ("chaos-mesh.org", "v1alpha1", "podchaos")
        }

        result = []

        # 如果指定了类型，只查询该类型
        if chaos_type and chaos_type in chaos_map:
            group, version, plural = chaos_map[chaos_type]
            result.extend(self._list_chaos_by_type(namespace, group, version, plural))
        else:
            # 查询所有类型
            for group, version, plural in chaos_map.values():
                result.extend(self._list_chaos_by_type(namespace, group, version, plural))

        return result

    def _list_chaos_by_type(self, namespace: str, group: str, 
                           version: str, plural: str) -> List[Dict]:
        """按类型列出故障"""
        try:
            response = self.custom_api.list_namespaced_custom_object(
                group=group,
                version=version,
                namespace=namespace,
                plural=plural
            )

            items = response.get('items', [])
            result = []

            for item in items:
                result.append({
                    "name": item['metadata']['name'],
                    "type": plural,
                    "namespace": item['metadata']['namespace'],
                    "created": item['metadata']['creationTimestamp'],
                    "status": item.get('status', {})
                })

            return result

        except Exception as e:
            logger.error(f"查询故障失败: {e}")
            return []

    def wait_chaos_completed(self, namespace: str, chaos_name: str, 
                            chaos_type: str, timeout: int = 300) -> Dict:
        """
        等待故障完成

        参数：
            namespace: 命名空间
            chaos_name: 故障名称
            chaos_type: 故障类型
            timeout: 超时时间（秒）

        返回：
            dict: 等待结果
        """
        result = {
            "chaos_name": chaos_name,
            "completed": False,
            "wait_time": None,
            "message": ""
        }

        chaos_map = {
            "stress": ("chaos-mesh.org", "v1alpha1", "stresschaos"),
            "network_delay": ("chaos-mesh.org", "v1alpha1", "networkchaos"),
            "network_loss": ("chaos-mesh.org", "v1alpha1", "networkchaos"),
            "io": ("chaos-mesh.org", "v1alpha1", "iochaos"),
            "pod_kill": ("chaos-mesh.org", "v1alpha1", "podchaos")
        }

        if chaos_type not in chaos_map:
            result["message"] = f"未知的故障类型: {chaos_type}"
            return result

        group, version, plural = chaos_map[chaos_type]

        start_time = time.time()
        logger.info(f"等待故障完成: {chaos_name}（超时: {timeout} 秒）")

        while time.time() - start_time < timeout:
            try:
                chaos = self.custom_api.get_namespaced_custom_object(
                    group=group,
                    version=version,
                    namespace=namespace,
                    plural=plural,
                    name=chaos_name
                )

                status = chaos.get('status', {})
                # 检查故障是否完成
                if status.get('phase') == 'Finished' or status.get('experiment') and status['experiment'].get('phase') == 'Finished':
                    wait_time = int(time.time() - start_time)
                    result["completed"] = True
                    result["wait_time"] = wait_time
                    result["message"] = f"故障在 {wait_time} 秒后完成"
                    logger.info(f"✓ 故障已完成: {chaos_name}")
                    return result

                time.sleep(5)

            except ApiException as e:
                if e.status == 404:
                    result["message"] = "故障不存在"
                    return result
                logger.error(f"查询故障状态失败: {e}")
                time.sleep(5)

        result["wait_time"] = int(time.time() - start_time)
        result["message"] = f"故障在 {timeout} 秒内未完成"
        logger.warning(f"⚠ 故障等待超时: {chaos_name}")
        return result

    def verify_chaos_injection(self, namespace: str, pod_name: str,
                            chaos_name: str, chaos_type: str) -> Dict:
        """
        验证故障是否真正注入成功
        
        参数：
            namespace: 命名空间
            pod_name: 目标 Pod 名称
            chaos_name: 故障名称
            chaos_type: 故障类型
            
        返回：
            dict: 验证结果
        """
        result = {
            "chaos_name": chaos_name,
            "pod_name": pod_name,
            "namespace": namespace,
            "verified": False,
            "details": {}
        }
        
        try:
            # 1. 检查 Chaos Mesh 资源状态
            chaos_map = {
                "stress": ("chaos-mesh.org", "v1alpha1", "stresschaos"),
                "network_delay": ("chaos-mesh.org", "v1alpha1", "networkchaos"),
                "network_loss": ("chaos-mesh.org", "v1alpha1", "networkchaos"),
                "io": ("chaos-mesh.org", "v1alpha1", "iochaos"),
                "pod_kill": ("chaos-mesh.org", "v1alpha1", "podchaos")
            }
            
            if chaos_type not in chaos_map:
                result["details"]["error"] = f"未知的故障类型: {chaos_type}"
                return result
            
            group, version, plural = chaos_map[chaos_type]
            
            try:
                chaos = self.custom_api.get_namespaced_custom_object(
                    group=group,
                    version=version,
                    namespace=namespace,
                    plural=plural,
                    name=chaos_name
                )
                result["details"]["chaos_status"] = chaos.get('status', {})
                result["details"]["chaos_phase"] = chaos.get('status', {}).get('phase', 'Unknown')
            except ApiException as e:
                result["details"]["chaos_error"] = f"Chaos 资源不存在: {e}"
                return result
            
            # 2. 检查 Pod 是否存在
            try:
                pod = self.v1.read_namespaced_pod(name=pod_name, namespace=namespace)
                result["details"]["pod_status"] = pod.status.phase
                result["details"]["pod_ready"] = all(
                    cs.ready for cs in pod.status.container_statuses or []
                )
            except ApiException as e:
                result["details"]["pod_error"] = f"Pod 不存在: {e}"
                return result
            
            # 3. 检查 Pod 是否有 Chaos Mesh sidecar
            containers = pod.spec.containers or []
            sidecar_names = [c.name for c in containers if 'chaos' in c.name.lower()]
            result["details"]["has_chaos_sidecar"] = len(sidecar_names) > 0
            result["details"]["sidecar_names"] = sidecar_names
            
            # 4. 检查 Pod 的注解
            annotations = pod.metadata.annotations or {}
            result["details"]["annotations"] = annotations
            
            # 5. 根据故障类型进行特定验证
            if chaos_type == "stress":
                # 检查 StressChaos 的实验状态
                status = chaos.get('status', {})
                experiment = status.get('experiment', {})
                result["details"]["experiment_phase"] = experiment.get('phase', 'Unknown')
                result["details"]["experiment_status"] = experiment.get('status', 'Unknown')
                
                # 检查是否选择了正确的 Pod
                selector = chaos.get('spec', {}).get('selector', {})
                result["details"]["selector"] = selector
            
            # 判断是否验证成功
            chaos_phase = result["details"].get("chaos_phase", "")
            experiment_phase = result["details"].get("experiment_phase", "")
            
            # Chaos 资源存在且实验正在运行
            if chaos_phase in ["Running", ""] and experiment_phase == "Running":
                result["verified"] = True
                result["details"]["message"] = "故障已成功注入并正在运行"
            else:
                result["details"]["message"] = f"故障状态异常: chaos_phase={chaos_phase}, experiment_phase={experiment_phase}"
            
        except Exception as e:
            result["details"]["error"] = f"验证过程中出错: {str(e)}"
        
        return result


def main():
    """主函数 - 用于测试"""
    print("=" * 60)
    print("应急演练自动化平台 - Chaos Mesh 故障注入模块")
    print("=" * 60)
    print()

    try:
        # 初始化 Chaos Mesh 注入器
        injector = ChaosMeshInjector()

        print("【使用说明】")
        print("-" * 60)
        print("Chaos Mesh 故障注入器支持以下功能：")
        print()
        print("1. CPU/内存压测:")
        print("   injector.create_stress_chaos(namespace, pod_name, cpu_count=2, memory_size='100Mi')")
        print()
        print("2. 网络延迟:")
        print("   injector.create_network_delay(namespace, pod_name, latency='100ms')")
        print()
        print("3. 网络丢包:")
        print("   injector.create_network_loss(namespace, pod_name, loss='50%')")
        print()
        print("4. 磁盘故障:")
        print("   injector.create_disk_failure(namespace, pod_name, fault_type='disk_fill')")
        print()
        print("5. Pod 杀死:")
        print("   injector.create_pod_kill(namespace, pod_name)")
        print()
        print("6. 列出所有故障:")
        print("   injector.list_chaos(namespace)")
        print()
        print("7. 删除故障:")
        print("   injector.delete_chaos(namespace, chaos_name, chaos_type)")
        print()
        print("【前置条件】")
        print("-" * 60)
        print("1. 已安装 Chaos Mesh（参考: https://chaos-mesh.org/docs/installation）")
        print("2. kubectl 已配置")
        print("3. 有相应的 Kubernetes 权限")
        print()

    except Exception as e:
        logger.error(f"初始化失败: {e}")
        print()
        print("请确保：")
        print("1. 已安装 Chaos Mesh")
        print("2. kubectl 配置正确")
        print("3. Python 依赖已安装（pip install kubernetes pyyaml）")


if __name__ == "__main__":
    main()
