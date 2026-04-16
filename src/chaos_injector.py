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
    from src.chaos_mesh_injector import ChaosMeshInjector
    CHAOS_MESH_AVAILABLE = True
except ImportError:
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

    def __init__(self, use_chaos_mesh: bool = False, kubeconfig_path: str = None,
                 cluster_api_server: str = None, cluster_token: str = None,
                 cluster_ca_cert: str = None):
        """
        初始化故障注入器

        参数：
            use_chaos_mesh: 是否使用 Chaos Mesh（默认 False）
            kubeconfig_path: kubeconfig 文件路径（可选，默认使用 ~/.kube/config）
            cluster_api_server: 集群 API Server 地址（可选，用于直接连接）
            cluster_token: 集群访问 Token（可选，用于直接连接）
            cluster_ca_cert: 集群 CA 证书内容（可选，用于直接连接）
        """
        self.use_chaos_mesh = use_chaos_mesh
        self.kubeconfig_path = kubeconfig_path
        self.cluster_api_server = cluster_api_server
        self.cluster_info = {}
        
        try:
            # 根据参数选择连接方式
            if cluster_api_server and cluster_token:
                # 使用 Token 直接连接集群
                self._connect_with_token(cluster_api_server, cluster_token, cluster_ca_cert)
            elif kubeconfig_path:
                # 使用指定的 kubeconfig 文件
                config.load_kube_config(config_file=kubeconfig_path)
                self.v1 = client.CoreV1Api()
                self.apps_v1 = client.AppsV1Api()
                logger.info(f"✓ Kubernetes 客户端初始化成功 (kubeconfig: {kubeconfig_path})")
            else:
                # 使用默认 kubeconfig
                config.load_kube_config()
                self.v1 = client.CoreV1Api()
                self.apps_v1 = client.AppsV1Api()
                logger.info("✓ Kubernetes 客户端初始化成功 (默认 kubeconfig)")
            
            # 获取集群信息
            self._get_cluster_info()
            
        except Exception as e:
            logger.error(f"✗ Kubernetes 客户端初始化失败: {e}")
            raise

        # 初始化 Chaos Mesh 注入器（如果需要）
        if use_chaos_mesh:
            if CHAOS_MESH_AVAILABLE:
                try:
                    self.chaos_mesh = ChaosMeshInjector(
                        kubeconfig_path=kubeconfig_path,
                        cluster_api_server=cluster_api_server,
                        cluster_token=cluster_token,
                        cluster_ca_cert=cluster_ca_cert
                    )
                    logger.info("✓ Chaos Mesh 注入器初始化成功")
                except Exception as e:
                    logger.error(f"✗ Chaos Mesh 注入器初始化失败: {e}")
                    logger.warning("将回退到原生 Kubernetes 故障注入")
                    self.use_chaos_mesh = False
            else:
                logger.warning("Chaos Mesh 注入器不可用，将使用原生 Kubernetes 故障注入")
                self.use_chaos_mesh = False

    def _connect_with_token(self, api_server: str, token: str, ca_cert: str = None):
        """使用 Token 连接集群"""
        import ssl
        import urllib3
        from kubernetes.client import Configuration, ApiClient

        # 去除末尾斜杠，避免路径拼接出现 //version/ 等双斜杠
        api_server = api_server.rstrip('/')

        # 禁用 SSL 警告
        urllib3.disable_warnings()

        # 优先尝试注入 PyOpenSSL（解决 macOS OpenSSL 3.x / LibreSSL 兼容问题）
        _pyopenssl_ok = False
        try:
            import urllib3.contrib.pyopenssl
            urllib3.contrib.pyopenssl.inject_into_urllib3()
            _pyopenssl_ok = True
            logger.info("✓ 已启用 PyOpenSSL SSL 后端")
        except ImportError:
            pass

        configuration = Configuration()
        configuration.host = api_server
        configuration.api_key = {"authorization": "Bearer " + token}
        configuration.verify_ssl = False
        configuration.ssl_ca_cert = None

        if ca_cert:
            import tempfile
            ca_cert_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.crt')
            ca_cert_file.write(ca_cert)
            ca_cert_file.close()
            configuration.ssl_ca_cert = ca_cert_file.name
            configuration.verify_ssl = True
        else:
            configuration.assert_hostname = False

        api_client = ApiClient(configuration)

        # PyOpenSSL 不可用时，注入自定义 SSL 上下文
        # OP_LEGACY_SERVER_CONNECT 是 Python 3.12 专门为兼容旧版 TLS 服务器引入的标志
        if not ca_cert and not _pyopenssl_ok:
            try:
                ssl_ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
                ssl_ctx.check_hostname = False
                ssl_ctx.verify_mode = ssl.CERT_NONE
                ssl_ctx.options |= ssl.OP_ALL
                if hasattr(ssl, 'OP_LEGACY_SERVER_CONNECT'):
                    ssl_ctx.options |= ssl.OP_LEGACY_SERVER_CONNECT
                api_client.rest_client.pool_manager = urllib3.PoolManager(
                    num_pools=4,
                    maxsize=4,
                    ssl_context=ssl_ctx,
                )
                logger.info("✓ 已注入自定义 SSL 上下文（含 OP_LEGACY_SERVER_CONNECT）")
            except Exception as e:
                logger.warning(f"自定义 SSL 上下文注入失败: {e}")

        self.v1 = client.CoreV1Api(api_client)
        self.apps_v1 = client.AppsV1Api(api_client)
        logger.info(f"✓ 使用 Token 连接集群成功: {api_server}")

    def _get_cluster_info(self):
        """获取集群基本信息（各项独立获取，互不影响）"""
        # 获取集群名称/上下文
        if self.cluster_api_server:
            self.cluster_info['context'] = 'token-connection'
            self.cluster_info['cluster'] = self.cluster_api_server
            self.cluster_info['cluster_name'] = self.cluster_api_server
        else:
            try:
                from kubernetes import config as k8s_config
                contexts = k8s_config.list_kube_config_contexts()
                if contexts:
                    current_context = contexts[1] if len(contexts) > 1 else contexts[0]
                    self.cluster_info['context'] = current_context.get('name', 'unknown')
                    self.cluster_info['cluster'] = current_context.get('context', {}).get('cluster', 'unknown')
                    self.cluster_info['cluster_name'] = current_context.get('name', 'unknown')
            except Exception:
                self.cluster_info['context'] = 'unknown'
                self.cluster_info['cluster'] = 'unknown'
                self.cluster_info['cluster_name'] = 'unknown'

        errors = {}

        # 获取 Kubernetes 版本
        try:
            version_info = client.VersionApi(self.v1.api_client).get_code()
            self.cluster_info['kubernetes_version'] = f"{version_info.major}.{version_info.minor}"
        except Exception as e:
            logger.warning(f"获取 Kubernetes 版本失败: {e}")
            self.cluster_info['kubernetes_version'] = 'unknown'
            errors['kubernetes_version'] = str(e)

        # 获取节点数量
        try:
            nodes = self.v1.list_node()
            self.cluster_info['node_count'] = len(nodes.items)
        except Exception as e:
            logger.warning(f"获取节点列表失败: {e}")
            self.cluster_info['node_count'] = 'unknown'
            errors['node_count'] = str(e)

        # 获取命名空间列表
        try:
            namespaces = self.v1.list_namespace()
            self.cluster_info['namespaces'] = [ns.metadata.name for ns in namespaces.items]
            logger.info(f"✓ 集群信息: 节点数 {self.cluster_info.get('node_count')}, {len(self.cluster_info['namespaces'])} 命名空间")
        except Exception as e:
            logger.warning(f"获取命名空间列表失败: {e}")
            self.cluster_info['namespaces'] = []
            errors['namespaces'] = str(e)

        if errors:
            self.cluster_info['_errors'] = errors

    def get_cluster_info(self) -> Dict:
        """返回集群信息"""
        return self.cluster_info

    def list_namespaces(self) -> list:
        """获取所有命名空间"""
        cached = self.cluster_info.get('namespaces')
        if cached:
            return cached
        # 缓存为空时实时获取
        try:
            namespaces = self.v1.list_namespace()
            ns_list = [ns.metadata.name for ns in namespaces.items]
            self.cluster_info['namespaces'] = ns_list
            return ns_list
        except Exception as e:
            logger.error(f"获取命名空间失败: {e}")
            return []

    def list_deployments(self, namespace: str) -> list:
        """获取指定命名空间的所有 Deployment"""
        try:
            deployments = self.apps_v1.list_namespaced_deployment(namespace)
            deploy_list = []
            for deploy in deployments.items:
                deploy_list.append({
                    'name': deploy.metadata.name,
                    'namespace': deploy.metadata.namespace,
                    'replicas': deploy.spec.replicas,
                    'available_replicas': deploy.status.available_replicas or 0,
                    'labels': deploy.metadata.labels or {}
                })
            return deploy_list
        except ApiException as e:
            logger.error(f"获取 Deployment 列表失败: {e}")
            return []

    def test_connection(self) -> Dict:
        """测试集群连接"""
        result = {
            'success': False,
            'message': '',
            'cluster_info': {}
        }
        try:
            # 测试 API 连接
            version = self.v1.get_api_resources()
            result['success'] = True
            result['message'] = '连接成功'
            result['cluster_info'] = self.cluster_info
        except Exception as e:
            result['message'] = f'连接失败: {str(e)}'
        return result

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
                         cpu_workers: Optional[int] = None,
                         cpu_load: Optional[int] = None,
                         memory_size: Optional[str] = None,
                         memory_workers: Optional[int] = None,
                         duration: str = "60s") -> Dict:
        """
        注入 CPU/内存压测故障

        参数：
            namespace: 命名空间
            pod_name: 目标 Pod 名称
            cpu_count: CPU 核心数（已废弃，建议使用 cpu_workers）
            cpu_workers: CPU 压测 workers 数量（默认 1）
            cpu_load: 每个 CPU worker 的负载百分比（1-100，默认 100）
            memory_size: 内存大小（如 100Mi, 1Gi，会自动转换为字节数）
            memory_workers: 内存压测 workers 数量（默认 1）
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

        return self.chaos_mesh.create_stress_chaos(
            namespace=namespace,
            pod_name=pod_name,
            cpu_count=cpu_count,
            cpu_workers=cpu_workers,
            cpu_load=cpu_load,
            memory_size=memory_size,
            memory_workers=memory_workers,
            duration=duration
        )

    def inject_memory_stress(self, namespace: str, pod_name: str,
                            memory_size: str = "256Mi",
                            memory_workers: Optional[int] = None,
                            duration: str = "60s") -> Dict:
        """
        注入内存压力故障

        参数：
            namespace: 命名空间
            pod_name: 目标 Pod 名称
            memory_size: 内存大小（如 256Mi, 512Mi, 1Gi）
            memory_workers: 内存压测 workers 数量（默认 1）
            duration: 持续时间

        返回：
            dict: 故障注入结果
        """
        if not self.use_chaos_mesh:
            logger.error("内存压测需要 Chaos Mesh，请初始化时设置 use_chaos_mesh=True")
            return {
                "scenario": "memory_stress",
                "success": False,
                "message": "内存压测需要 Chaos Mesh"
            }

        return self.chaos_mesh.create_stress_chaos(
            namespace=namespace,
            pod_name=pod_name,
            cpu_count=None,
            cpu_workers=None,
            memory_size=memory_size,
            memory_workers=memory_workers,
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

    def exec_script(self, namespace: str, pod_name: str, script: str,
                    container: str = None, timeout: int = 60) -> Dict:
        """
        在指定 Pod 内执行自定义 shell 脚本

        参数：
            namespace: 命名空间
            pod_name: 目标 Pod 名称
            script: 要执行的 shell 脚本内容
            container: 容器名称（可选，不指定时使用第一个容器）
            timeout: 执行超时时间（秒）

        返回：
            dict: {'success': bool, 'stdout': str, 'stderr': str, 'message': str}
        """
        from kubernetes.stream import stream

        result = {
            'scenario': 'custom_script',
            'namespace': namespace,
            'pod_name': pod_name,
            'inject_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'success': False,
            'stdout': '',
            'stderr': '',
            'message': '',
        }

        try:
            exec_command = ['/bin/sh', '-c', script]
            kwargs = dict(
                name=pod_name,
                namespace=namespace,
                command=exec_command,
                stderr=True,
                stdin=False,
                stdout=True,
                tty=False,
                _preload_content=True,
            )
            if container:
                kwargs['container'] = container

            resp = stream(self.v1.connect_get_namespaced_pod_exec, **kwargs)

            # resp is the combined stdout string when _preload_content=True
            result['stdout'] = resp if isinstance(resp, str) else ''
            result['success'] = True
            result['message'] = '脚本执行完成'
            logger.info(f"✓ 脚本在 {namespace}/{pod_name} 执行成功")
        except ApiException as e:
            result['message'] = f'Kubernetes API 错误: {e.status} - {e.reason}'
            result['stderr'] = str(e)
            logger.error(f"✗ 脚本执行失败: {e}")
        except Exception as e:
            result['message'] = f'脚本执行异常: {e}'
            result['stderr'] = str(e)
            logger.error(f"✗ 脚本执行异常: {e}")

        return result

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
