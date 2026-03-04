"""
chaos_mesh_injector.py 的单元测试
测试 ChaosMeshInjector 类
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import yaml


# 导入要测试的模块
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "emergency-drill-platform" / "src"))
from chaos_mesh_injector import ChaosMeshInjector


@pytest.mark.unit
class TestChaosMeshInjectorInit:
    """测试 ChaosMeshInjector 初始化"""

    @patch('chaos_mesh_injector.config.load_kube_config')
    @patch('chaos_mesh_injector.client.CustomObjectsApi')
    def test_init_with_kubeconfig(self, mock_custom_api, mock_load_config):
        """测试使用 kubeconfig 初始化"""
        injector = ChaosMeshInjector()

        mock_load_config.assert_called_once()
        mock_custom_api.assert_called_once()
        assert injector.custom_api is not None

    @patch('chaos_mesh_injector.config.load_kube_config')
    @patch('chaos_mesh_injector.config.load_incluster_config')
    @patch('chaos_mesh_injector.client.CustomObjectsApi')
    def test_init_fallback_to_incluster(self, mock_custom_api, mock_incluster, mock_load_config):
        """测试回退到集群内配置"""
        mock_load_config.side_effect = Exception("kubeconfig not found")

        injector = ChaosMeshInjector()

        mock_load_config.assert_called_once()
        mock_incluster.assert_called_once()


@pytest.mark.unit
class TestChaosMeshInjectorPodChaos:
    """测试 Pod 混沌实验"""

    @patch('chaos_mesh_injector.config.load_kube_config')
    @patch('chaos_mesh_injector.client.CustomObjectsApi')
    def test_create_pod_kill_chaos_success(self, mock_custom_api, mock_load_config):
        """测试成功创建 Pod Kill 混沌实验"""
        mock_api = MagicMock()
        mock_custom_api.return_value = mock_api

        injector = ChaosMeshInjector()
        result = injector.create_pod_kill_chaos(
            name="test-chaos",
            namespace="default",
            selector={"app": "test"}
        )

        assert result is True
        mock_api.create_namespaced_custom_object.assert_called_once()

    @patch('chaos_mesh_injector.config.load_kube_config')
    @patch('chaos_mesh_injector.client.CustomObjectsApi')
    def test_create_pod_kill_chaos_with_duration(self, mock_custom_api, mock_load_config):
        """测试创建带持续时间的 Pod Kill 混沌实验"""
        mock_api = MagicMock()
        mock_custom_api.return_value = mock_api

        injector = ChaosMeshInjector()
        result = injector.create_pod_kill_chaos(
            name="test-chaos",
            namespace="default",
            selector={"app": "test"},
            duration="30s"
        )

        assert result is True
        # 验证调用参数
        call_args = mock_api.create_namespaced_custom_object.call_args
        body = call_args[1]['body']
        assert body['spec']['duration'] == "30s"

    @patch('chaos_mesh_injector.config.load_kube_config')
    @patch('chaos_mesh_injector.client.CustomObjectsApi')
    def test_create_pod_kill_chaos_api_error(self, mock_custom_api, mock_load_config):
        """测试 API 错误"""
        mock_api = MagicMock()
        mock_api.create_namespaced_custom_object.side_effect = Exception("API Error")
        mock_custom_api.return_value = mock_api

        injector = ChaosMeshInjector()
        result = injector.create_pod_kill_chaos(
            name="test-chaos",
            namespace="default",
            selector={"app": "test"}
        )

        assert result is False


@pytest.mark.unit
class TestChaosMeshInjectorNetworkChaos:
    """测试网络混沌实验"""

    @patch('chaos_mesh_injector.config.load_kube_config')
    @patch('chaos_mesh_injector.client.CustomObjectsApi')
    def test_create_network_delay_chaos_success(self, mock_custom_api, mock_load_config):
        """测试成功创建网络延迟混沌实验"""
        mock_api = MagicMock()
        mock_custom_api.return_value = mock_api

        injector = ChaosMeshInjector()
        result = injector.create_network_delay_chaos(
            name="test-network-chaos",
            namespace="default",
            selector={"app": "test"},
            delay="100ms"
        )

        assert result is True
        mock_api.create_namespaced_custom_object.assert_called_once()

    @patch('chaos_mesh_injector.config.load_kube_config')
    @patch('chaos_mesh_injector.client.CustomObjectsApi')
    def test_create_network_loss_chaos_success(self, mock_custom_api, mock_load_config):
        """测试成功创建网络丢包混沌实验"""
        mock_api = MagicMock()
        mock_custom_api.return_value = mock_api

        injector = ChaosMeshInjector()
        result = injector.create_network_loss_chaos(
            name="test-network-loss",
            namespace="default",
            selector={"app": "test"},
            loss="50"
        )

        assert result is True


@pytest.mark.unit
class TestChaosMeshInjectorStressChaos:
    """测试压力混沌实验"""

    @patch('chaos_mesh_injector.config.load_kube_config')
    @patch('chaos_mesh_injector.client.CustomObjectsApi')
    def test_create_cpu_stress_chaos_success(self, mock_custom_api, mock_load_config):
        """测试成功创建 CPU 压力混沌实验"""
        mock_api = MagicMock()
        mock_custom_api.return_value = mock_api

        injector = ChaosMeshInjector()
        result = injector.create_cpu_stress_chaos(
            name="test-cpu-stress",
            namespace="default",
            selector={"app": "test"},
            workers=2
        )

        assert result is True

    @patch('chaos_mesh_injector.config.load_kube_config')
    @patch('chaos_mesh_injector.client.CustomObjectsApi')
    def test_create_memory_stress_chaos_success(self, mock_custom_api, mock_load_config):
        """测试成功创建内存压力混沌实验"""
        mock_api = MagicMock()
        mock_custom_api.return_value = mock_api

        injector = ChaosMeshInjector()
        result = injector.create_memory_stress_chaos(
            name="test-memory-stress",
            namespace="default",
            selector={"app": "test"},
            size="512Mi"
        )

        assert result is True


@pytest.mark.unit
class TestChaosMeshInjectorChaosManagement:
    """测试混沌实验管理"""

    @patch('chaos_mesh_injector.config.load_kube_config')
    @patch('chaos_mesh_injector.client.CustomObjectsApi')
    def test_delete_chaos_success(self, mock_custom_api, mock_load_config):
        """测试成功删除混沌实验"""
        mock_api = MagicMock()
        mock_custom_api.return_value = mock_api

        injector = ChaosMeshInjector()
        result = injector.delete_chaos(
            name="test-chaos",
            namespace="default",
            chaos_type="PodChaos"
        )

        assert result is True
        mock_api.delete_namespaced_custom_object.assert_called_once()

    @patch('chaos_mesh_injector.config.load_kube_config')
    @patch('chaos_mesh_injector.client.CustomObjectsApi')
    def test_delete_chaos_not_found(self, mock_custom_api, mock_load_config):
        """测试删除不存在的混沌实验"""
        mock_api = MagicMock()
        mock_api.delete_namespaced_custom_object.side_effect = Exception("Not Found")
        mock_custom_api.return_value = mock_api

        injector = ChaosMeshInjector()
        result = injector.delete_chaos(
            name="nonexistent-chaos",
            namespace="default",
            chaos_type="PodChaos"
        )

        assert result is False

    @patch('chaos_mesh_injector.config.load_kube_config')
    @patch('chaos_mesh_injector.client.CustomObjectsApi')
    def test_list_chaos_experiments_success(self, mock_custom_api, mock_load_config):
        """测试成功列出混沌实验"""
        mock_api = MagicMock()
        mock_api.list_namespaced_custom_object.return_value = {
            "items": [
                {"metadata": {"name": "chaos-1"}},
                {"metadata": {"name": "chaos-2"}}
            ]
        }
        mock_custom_api.return_value = mock_api

        injector = ChaosMeshInjector()
        result = injector.list_chaos_experiments(
            namespace="default",
            chaos_type="PodChaos"
        )

        assert len(result) == 2
        assert result[0]["metadata"]["name"] == "chaos-1"

    @patch('chaos_mesh_injector.config.load_kube_config')
    @patch('chaos_mesh_injector.client.CustomObjectsApi')
    def test_get_chaos_status_success(self, mock_custom_api, mock_load_config):
        """测试成功获取混沌实验状态"""
        mock_api = MagicMock()
        mock_api.get_namespaced_custom_object.return_value = {
            "metadata": {"name": "test-chaos"},
            "status": {"phase": "Running"}
        }
        mock_custom_api.return_value = mock_api

        injector = ChaosMeshInjector()
        result = injector.get_chaos_status(
            name="test-chaos",
            namespace="default",
            chaos_type="PodChaos"
        )

        assert result is not None
        assert result["status"]["phase"] == "Running"


@pytest.mark.unit
class TestChaosMeshInjectorEdgeCases:
    """测试边界情况"""

    @patch('chaos_mesh_injector.config.load_kube_config')
    @patch('chaos_mesh_injector.client.CustomObjectsApi')
    def test_empty_chaos_name(self, mock_custom_api, mock_load_config):
        """测试空混沌实验名称"""
        injector = ChaosMeshInjector()

        with pytest.raises(Exception):
            injector.create_pod_kill_chaos(
                name="",
                namespace="default",
                selector={"app": "test"}
            )

    @patch('chaos_mesh_injector.config.load_kube_config')
    @patch('chaos_mesh_injector.client.CustomObjectsApi')
    def test_empty_namespace(self, mock_custom_api, mock_load_config):
        """测试空命名空间"""
        injector = ChaosMeshInjector()

        with pytest.raises(Exception):
            injector.create_pod_kill_chaos(
                name="test-chaos",
                namespace="",
                selector={"app": "test"}
            )

    @patch('chaos_mesh_injector.config.load_kube_config')
    @patch('chaos_mesh_injector.client.CustomObjectsApi')
    def test_empty_selector(self, mock_custom_api, mock_load_config):
        """测试空选择器"""
        injector = ChaosMeshInjector()

        with pytest.raises(Exception):
            injector.create_pod_kill_chaos(
                name="test-chaos",
                namespace="default",
                selector={}
            )

    @patch('chaos_mesh_injector.config.load_kube_config')
    @patch('chaos_mesh_injector.client.CustomObjectsApi')
    def test_invalid_duration_format(self, mock_custom_api, mock_load_config):
        """测试无效的持续时间格式"""
        mock_api = MagicMock()
        mock_custom_api.return_value = mock_api

        injector = ChaosMeshInjector()
        result = injector.create_pod_kill_chaos(
            name="test-chaos",
            namespace="default",
            selector={"app": "test"},
            duration="invalid"
        )

        # 应该仍然创建，但可能在 Chaos Mesh 端失败
        assert result is True

    @patch('chaos_mesh_injector.config.load_kube_config')
    @patch('chaos_mesh_injector.client.CustomObjectsApi')
    def test_negative_workers(self, mock_custom_api, mock_load_config):
        """测试负数 workers"""
        injector = ChaosMeshInjector()

        result = injector.create_cpu_stress_chaos(
            name="test-cpu-stress",
            namespace="default",
            selector={"app": "test"},
            workers=-1
        )

        assert result is False
