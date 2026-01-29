"""
集成测试 - 测试完整的混沌工程演练流程
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import time


# 导入要测试的模块
import sys
from pathlib import Path
src_path = Path(__file__).parent.parent.parent / "emergency-drill-platform" / "src"
sys.path.insert(0, str(src_path))

from monitor_checker import MonitorChecker
from chaos_injector import ChaosInjector
from chaos_mesh_injector import ChaosMeshInjector


@pytest.mark.integration
class TestEndToEndDrill:
    """端到端混沌演练测试"""

    @patch('chaos_injector.config.load_kube_config')
    @patch('chaos_injector.client.CoreV1Api')
    @patch('monitor_checker.requests.get')
    def test_pod_kill_and_alert_verification(self, mock_get, mock_core_api, mock_load_config):
        """测试 Pod 删除和告警验证的完整流程"""
        # 1. 设置 Kubernetes mock
        mock_v1 = MagicMock()
        mock_core_api.return_value = mock_v1

        # 2. 设置 Prometheus mock - 模拟告警触发
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "success",
            "data": {
                "alerts": [
                    {
                        "labels": {
                            "alertname": "PodCrashLooping",
                            "severity": "critical",
                            "pod": "test-pod"
                        },
                        "state": "firing"
                    }
                ]
            }
        }
        mock_get.return_value = mock_response

        # 3. 执行混沌注入
        chaos_injector = ChaosInjector()
        kill_result = chaos_injector.kill_pod("test-pod", "default")
        assert kill_result is True

        # 4. 验证告警触发
        monitor = MonitorChecker("http://localhost:9090")
        alert = monitor.query_alert_by_name("PodCrashLooping")
        assert alert is not None
        assert alert["labels"]["alertname"] == "PodCrashLooping"

    @patch('chaos_mesh_injector.config.load_kube_config')
    @patch('chaos_mesh_injector.client.CustomObjectsApi')
    @patch('monitor_checker.requests.get')
    @patch('monitor_checker.time.sleep', return_value=None)
    @patch('monitor_checker.time.time')
    def test_chaos_mesh_network_delay_drill(
        self, mock_time, mock_sleep, mock_get, mock_custom_api, mock_load_config
    ):
        """测试 Chaos Mesh 网络延迟演练"""
        # 1. 设置 Chaos Mesh mock
        mock_api = MagicMock()
        mock_custom_api.return_value = mock_api

        # 2. 创建网络延迟混沌实验
        chaos_mesh = ChaosMeshInjector()
        create_result = chaos_mesh.create_network_delay_chaos(
            name="network-delay-test",
            namespace="default",
            selector={"app": "test"},
            delay="100ms"
        )
        assert create_result is True

        # 3. 模拟时间流逝和告警触发
        mock_time.side_effect = [0, 5, 10]
        mock_response = Mock()
        mock_response.status_code = 200

        # 第一次查询无告警，第二次有告警
        mock_response.json.side_effect = [
            {"status": "success", "data": {"alerts": []}},
            {
                "status": "success",
                "data": {
                    "alerts": [
                        {
                            "labels": {
                                "alertname": "HighLatency",
                                "severity": "warning"
                            },
                            "state": "firing"
                        }
                    ]
                }
            }
        ]
        mock_get.return_value = mock_response

        # 4. 等待告警触发
        monitor = MonitorChecker("http://localhost:9090")
        result = monitor.wait_for_alert("HighLatency", timeout=30, check_interval=5)
        assert result["triggered"] is True

        # 5. 清理混沌实验
        delete_result = chaos_mesh.delete_chaos(
            name="network-delay-test",
            namespace="default",
            chaos_type="NetworkChaos"
        )
        assert delete_result is True


@pytest.mark.integration
class TestMultiStepDrill:
    """多步骤混沌演练测试"""

    @patch('chaos_injector.config.load_kube_config')
    @patch('chaos_injector.client.CoreV1Api')
    @patch('monitor_checker.requests.get')
    def test_sequential_chaos_injection(self, mock_get, mock_core_api, mock_load_config):
        """测试顺序混沌注入"""
        mock_v1 = MagicMock()
        mock_pod = MagicMock()
        mock_pod.metadata.name = "test-pod"
        mock_v1.list_namespaced_pod.return_value.items = [mock_pod]
        mock_core_api.return_value = mock_v1

        # 设置 Prometheus 响应
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "success",
            "data": {"alerts": []}
        }
        mock_get.return_value = mock_response

        chaos_injector = ChaosInjector()
        monitor = MonitorChecker("http://localhost:9090")

        # 步骤 1: 注入 CPU 压力
        with patch('chaos_injector.stream.stream') as mock_stream:
            mock_stream.return_value = "success"
            cpu_result = chaos_injector.inject_cpu_stress(
                namespace="default",
                pod_selector="app=test",
                cpu_cores=2,
                duration_seconds=30
            )
            assert cpu_result is True

        # 步骤 2: 验证初始状态
        alerts = monitor.query_alerts()
        assert isinstance(alerts, list)

        # 步骤 3: 注入内存压力
        with patch('chaos_injector.stream.stream') as mock_stream:
            mock_stream.return_value = "success"
            memory_result = chaos_injector.inject_memory_stress(
                namespace="default",
                pod_selector="app=test",
                memory_mb=512,
                duration_seconds=30
            )
            assert memory_result is True


@pytest.mark.integration
@pytest.mark.slow
class TestRealWorldScenarios:
    """真实场景测试"""

    @patch('chaos_mesh_injector.config.load_kube_config')
    @patch('chaos_mesh_injector.client.CustomObjectsApi')
    @patch('monitor_checker.requests.get')
    def test_microservice_failure_scenario(
        self, mock_get, mock_custom_api, mock_load_config
    ):
        """测试微服务故障场景"""
        # 模拟微服务架构中的故障场景
        mock_api = MagicMock()
        mock_custom_api.return_value = mock_api

        chaos_mesh = ChaosMeshInjector()
        monitor = MonitorChecker("http://localhost:9090")

        # 场景：前端服务调用后端服务失败
        # 1. 注入网络分区
        partition_result = chaos_mesh.create_network_loss_chaos(
            name="network-partition",
            namespace="default",
            selector={"app": "backend"},
            loss="100"
        )
        assert partition_result is True

        # 2. 验证告警
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "success",
            "data": {
                "alerts": [
                    {
                        "labels": {
                            "alertname": "ServiceUnavailable",
                            "service": "backend"
                        },
                        "state": "firing"
                    }
                ]
            }
        }
        mock_get.return_value = mock_response

        alert = monitor.query_alert_by_name("ServiceUnavailable")
        assert alert is not None


@pytest.mark.integration
class TestErrorHandling:
    """集成测试 - 错误处理"""

    @patch('chaos_injector.config.load_kube_config')
    @patch('chaos_injector.client.CoreV1Api')
    def test_chaos_injection_failure_handling(self, mock_core_api, mock_load_config):
        """测试混沌注入失败的处理"""
        mock_v1 = MagicMock()
        mock_v1.delete_namespaced_pod.side_effect = Exception("API Error")
        mock_core_api.return_value = mock_v1

        chaos_injector = ChaosInjector()
        result = chaos_injector.kill_pod("test-pod", "default")

        # 应该优雅地处理错误
        assert result is False

    @patch('monitor_checker.requests.get')
    def test_prometheus_connection_failure(self, mock_get):
        """测试 Prometheus 连接失败"""
        mock_get.side_effect = Exception("Connection refused")

        monitor = MonitorChecker("http://localhost:9090")
        alerts = monitor.query_alerts()

        # 应该返回空列表而不是崩溃
        assert alerts == []


@pytest.mark.integration
class TestConcurrentOperations:
    """并发操作测试"""

    @patch('chaos_injector.config.load_kube_config')
    @patch('chaos_injector.client.CoreV1Api')
    def test_multiple_chaos_injections(self, mock_core_api, mock_load_config):
        """测试多个混沌注入"""
        mock_v1 = MagicMock()
        mock_pod1 = MagicMock()
        mock_pod1.metadata.name = "test-pod-1"
        mock_pod2 = MagicMock()
        mock_pod2.metadata.name = "test-pod-2"
        mock_v1.list_namespaced_pod.return_value.items = [mock_pod1, mock_pod2]
        mock_core_api.return_value = mock_v1

        chaos_injector = ChaosInjector()

        # 同时删除多个 Pod
        results = []
        for i in range(1, 3):
            result = chaos_injector.kill_pod(f"test-pod-{i}", "default")
            results.append(result)

        # 所有操作都应该成功
        assert all(results)


@pytest.mark.integration
class TestDrillWorkflow:
    """完整演练工作流测试"""

    @patch('chaos_mesh_injector.config.load_kube_config')
    @patch('chaos_mesh_injector.client.CustomObjectsApi')
    @patch('monitor_checker.requests.get')
    @patch('monitor_checker.time.sleep', return_value=None)
    @patch('monitor_checker.time.time')
    def test_complete_drill_workflow(
        self, mock_time, mock_sleep, mock_get, mock_custom_api, mock_load_config
    ):
        """测试完整的演练工作流"""
        # 1. 初始化
        mock_api = MagicMock()
        mock_custom_api.return_value = mock_api

        chaos_mesh = ChaosMeshInjector()
        monitor = MonitorChecker("http://localhost:9090")

        # 2. 创建混沌实验
        create_result = chaos_mesh.create_pod_kill_chaos(
            name="drill-test",
            namespace="default",
            selector={"app": "test"},
            duration="30s"
        )
        assert create_result is True

        # 3. 获取混沌实验状态
        mock_api.get_namespaced_custom_object.return_value = {
            "metadata": {"name": "drill-test"},
            "status": {"phase": "Running"}
        }
        status = chaos_mesh.get_chaos_status(
            name="drill-test",
            namespace="default",
            chaos_type="PodChaos"
        )
        assert status["status"]["phase"] == "Running"

        # 4. 等待告警触发
        mock_time.side_effect = [0, 5, 10]
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.side_effect = [
            {"status": "success", "data": {"alerts": []}},
            {
                "status": "success",
                "data": {
                    "alerts": [
                        {
                            "labels": {"alertname": "PodKilled"},
                            "state": "firing"
                        }
                    ]
                }
            }
        ]
        mock_get.return_value = mock_response

        alert_result = monitor.wait_for_alert("PodKilled", timeout=30, check_interval=5)
        assert alert_result["triggered"] is True

        # 5. 清理
        delete_result = chaos_mesh.delete_chaos(
            name="drill-test",
            namespace="default",
            chaos_type="PodChaos"
        )
        assert delete_result is True

        # 6. 验证清理完成
        mock_api.list_namespaced_custom_object.return_value = {"items": []}
        experiments = chaos_mesh.list_chaos_experiments(
            namespace="default",
            chaos_type="PodChaos"
        )
        assert len(experiments) == 0
