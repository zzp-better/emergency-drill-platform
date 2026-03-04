"""
chaos_injector.py 的单元测试
测试 ChaosInjector 类
"""
import pytest
from unittest.mock import Mock, patch, MagicMock, call
from kubernetes.client.rest import ApiException


# 导入要测试的模块
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "emergency-drill-platform" / "src"))
from chaos_injector import ChaosInjector


@pytest.mark.unit
class TestChaosInjectorInit:
    """测试 ChaosInjector 初始化"""

    @patch('chaos_injector.config.load_kube_config')
    @patch('chaos_injector.client.CoreV1Api')
    def test_init_with_kubeconfig(self, mock_core_api, mock_load_config):
        """测试使用 kubeconfig 初始化"""
        injector = ChaosInjector()

        mock_load_config.assert_called_once()
        mock_core_api.assert_called_once()
        assert injector.v1 is not None

    @patch('chaos_injector.config.load_kube_config')
    @patch('chaos_injector.config.load_incluster_config')
    @patch('chaos_injector.client.CoreV1Api')
    def test_init_fallback_to_incluster(self, mock_core_api, mock_incluster, mock_load_config):
        """测试回退到集群内配置"""
        mock_load_config.side_effect = Exception("kubeconfig not found")

        injector = ChaosInjector()

        mock_load_config.assert_called_once()
        mock_incluster.assert_called_once()
        mock_core_api.assert_called_once()


@pytest.mark.unit
class TestChaosInjectorPodKill:
    """测试 Pod 删除功能"""

    @patch('chaos_injector.config.load_kube_config')
    @patch('chaos_injector.client.CoreV1Api')
    def test_kill_pod_success(self, mock_core_api, mock_load_config):
        """测试成功删除 Pod"""
        mock_v1 = MagicMock()
        mock_core_api.return_value = mock_v1

        injector = ChaosInjector()
        result = injector.kill_pod("test-pod", "default")

        assert result is True
        mock_v1.delete_namespaced_pod.assert_called_once_with(
            name="test-pod",
            namespace="default"
        )

    @patch('chaos_injector.config.load_kube_config')
    @patch('chaos_injector.client.CoreV1Api')
    def test_kill_pod_not_found(self, mock_core_api, mock_load_config):
        """测试删除不存在的 Pod"""
        mock_v1 = MagicMock()
        mock_v1.delete_namespaced_pod.side_effect = ApiException(status=404, reason="Not Found")
        mock_core_api.return_value = mock_v1

        injector = ChaosInjector()
        result = injector.kill_pod("nonexistent-pod", "default")

        assert result is False

    @patch('chaos_injector.config.load_kube_config')
    @patch('chaos_injector.client.CoreV1Api')
    def test_kill_pod_api_error(self, mock_core_api, mock_load_config):
        """测试 API 错误"""
        mock_v1 = MagicMock()
        mock_v1.delete_namespaced_pod.side_effect = ApiException(status=500, reason="Internal Error")
        mock_core_api.return_value = mock_v1

        injector = ChaosInjector()
        result = injector.kill_pod("test-pod", "default")

        assert result is False


@pytest.mark.unit
class TestChaosInjectorNetworkDelay:
    """测试网络延迟注入功能"""

    @patch('chaos_injector.config.load_kube_config')
    @patch('chaos_injector.client.CoreV1Api')
    def test_inject_network_delay_success(self, mock_core_api, mock_load_config):
        """测试成功注入网络延迟"""
        mock_v1 = MagicMock()

        # 模拟 Pod 列表
        mock_pod = MagicMock()
        mock_pod.metadata.name = "test-pod"
        mock_v1.list_namespaced_pod.return_value.items = [mock_pod]

        # 模拟 exec 命令成功
        mock_stream = MagicMock()
        mock_core_api.return_value = mock_v1

        with patch('chaos_injector.stream.stream') as mock_stream_func:
            mock_stream_func.return_value = "success"

            injector = ChaosInjector()
            result = injector.inject_network_delay(
                namespace="default",
                pod_selector="app=test",
                delay_ms=100
            )

            assert result is True

    @patch('chaos_injector.config.load_kube_config')
    @patch('chaos_injector.client.CoreV1Api')
    def test_inject_network_delay_no_pods(self, mock_core_api, mock_load_config):
        """测试没有匹配的 Pod"""
        mock_v1 = MagicMock()
        mock_v1.list_namespaced_pod.return_value.items = []
        mock_core_api.return_value = mock_v1

        injector = ChaosInjector()
        result = injector.inject_network_delay(
            namespace="default",
            pod_selector="app=nonexistent",
            delay_ms=100
        )

        assert result is False


@pytest.mark.unit
class TestChaosInjectorCPUStress:
    """测试 CPU 压力测试功能"""

    @patch('chaos_injector.config.load_kube_config')
    @patch('chaos_injector.client.CoreV1Api')
    def test_inject_cpu_stress_success(self, mock_core_api, mock_load_config):
        """测试成功注入 CPU 压力"""
        mock_v1 = MagicMock()
        mock_pod = MagicMock()
        mock_pod.metadata.name = "test-pod"
        mock_v1.list_namespaced_pod.return_value.items = [mock_pod]
        mock_core_api.return_value = mock_v1

        with patch('chaos_injector.stream.stream') as mock_stream_func:
            mock_stream_func.return_value = "success"

            injector = ChaosInjector()
            result = injector.inject_cpu_stress(
                namespace="default",
                pod_selector="app=test",
                cpu_cores=2,
                duration_seconds=60
            )

            assert result is True


@pytest.mark.unit
class TestChaosInjectorMemoryStress:
    """测试内存压力测试功能"""

    @patch('chaos_injector.config.load_kube_config')
    @patch('chaos_injector.client.CoreV1Api')
    def test_inject_memory_stress_success(self, mock_core_api, mock_load_config):
        """测试成功注入内存压力"""
        mock_v1 = MagicMock()
        mock_pod = MagicMock()
        mock_pod.metadata.name = "test-pod"
        mock_v1.list_namespaced_pod.return_value.items = [mock_pod]
        mock_core_api.return_value = mock_v1

        with patch('chaos_injector.stream.stream') as mock_stream_func:
            mock_stream_func.return_value = "success"

            injector = ChaosInjector()
            result = injector.inject_memory_stress(
                namespace="default",
                pod_selector="app=test",
                memory_mb=512,
                duration_seconds=60
            )

            assert result is True


@pytest.mark.unit
class TestChaosInjectorCleanup:
    """测试清理功能"""

    @patch('chaos_injector.config.load_kube_config')
    @patch('chaos_injector.client.CoreV1Api')
    def test_cleanup_chaos_success(self, mock_core_api, mock_load_config):
        """测试成功清理混沌实验"""
        mock_v1 = MagicMock()
        mock_pod = MagicMock()
        mock_pod.metadata.name = "test-pod"
        mock_v1.list_namespaced_pod.return_value.items = [mock_pod]
        mock_core_api.return_value = mock_v1

        with patch('chaos_injector.stream.stream') as mock_stream_func:
            mock_stream_func.return_value = "success"

            injector = ChaosInjector()
            result = injector.cleanup_chaos(
                namespace="default",
                pod_selector="app=test"
            )

            assert result is True


@pytest.mark.unit
class TestChaosInjectorEdgeCases:
    """测试边界情况"""

    @patch('chaos_injector.config.load_kube_config')
    @patch('chaos_injector.client.CoreV1Api')
    def test_empty_namespace(self, mock_core_api, mock_load_config):
        """测试空命名空间"""
        injector = ChaosInjector()

        with pytest.raises(Exception):
            injector.kill_pod("test-pod", "")

    @patch('chaos_injector.config.load_kube_config')
    @patch('chaos_injector.client.CoreV1Api')
    def test_empty_pod_name(self, mock_core_api, mock_load_config):
        """测试空 Pod 名称"""
        injector = ChaosInjector()

        with pytest.raises(Exception):
            injector.kill_pod("", "default")

    @patch('chaos_injector.config.load_kube_config')
    @patch('chaos_injector.client.CoreV1Api')
    def test_negative_delay(self, mock_core_api, mock_load_config):
        """测试负数延迟"""
        injector = ChaosInjector()

        result = injector.inject_network_delay(
            namespace="default",
            pod_selector="app=test",
            delay_ms=-100
        )

        assert result is False

    @patch('chaos_injector.config.load_kube_config')
    @patch('chaos_injector.client.CoreV1Api')
    def test_zero_cpu_cores(self, mock_core_api, mock_load_config):
        """测试零 CPU 核心"""
        injector = ChaosInjector()

        result = injector.inject_cpu_stress(
            namespace="default",
            pod_selector="app=test",
            cpu_cores=0,
            duration_seconds=60
        )

        assert result is False
