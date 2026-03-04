"""
Pytest 配置和共享 fixtures
"""
import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, MagicMock
from typing import Dict, List

# 添加 src 目录到 Python 路径
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))


# ============================================================================
# Mock Fixtures - Prometheus
# ============================================================================

@pytest.fixture
def mock_prometheus_response():
    """模拟 Prometheus API 响应"""
    return {
        "status": "success",
        "data": {
            "alerts": [
                {
                    "labels": {
                        "alertname": "PodCrashLooping",
                        "severity": "critical",
                        "namespace": "default",
                        "pod": "test-pod"
                    },
                    "annotations": {
                        "summary": "Pod is crash looping",
                        "description": "Pod test-pod is crash looping"
                    },
                    "state": "firing",
                    "activeAt": "2024-01-01T00:00:00Z",
                    "value": "1"
                }
            ]
        }
    }


@pytest.fixture
def mock_prometheus_query_response():
    """模拟 Prometheus 查询响应"""
    return {
        "status": "success",
        "data": {
            "resultType": "vector",
            "result": [
                {
                    "metric": {
                        "__name__": "up",
                        "job": "kubernetes-pods",
                        "instance": "10.0.0.1:8080"
                    },
                    "value": [1704067200, "1"]
                }
            ]
        }
    }


@pytest.fixture
def mock_requests_get(monkeypatch, mock_prometheus_response):
    """模拟 requests.get 方法"""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = mock_prometheus_response
    mock_response.raise_for_status = Mock()

    def mock_get(*args, **kwargs):
        return mock_response

    monkeypatch.setattr("requests.get", mock_get)
    return mock_response


# ============================================================================
# Mock Fixtures - Kubernetes
# ============================================================================

@pytest.fixture
def mock_k8s_client():
    """模拟 Kubernetes 客户端"""
    mock_client = MagicMock()

    # 模拟 Pod 对象
    mock_pod = MagicMock()
    mock_pod.metadata.name = "test-pod"
    mock_pod.metadata.namespace = "default"
    mock_pod.status.phase = "Running"

    # 模拟 API 响应
    mock_client.list_namespaced_pod.return_value.items = [mock_pod]
    mock_client.read_namespaced_pod.return_value = mock_pod

    return mock_client


@pytest.fixture
def mock_k8s_config(monkeypatch):
    """模拟 Kubernetes 配置加载"""
    def mock_load_config():
        pass

    monkeypatch.setattr("kubernetes.config.load_kube_config", mock_load_config)
    monkeypatch.setattr("kubernetes.config.load_incluster_config", mock_load_config)


# ============================================================================
# Test Data Fixtures
# ============================================================================

@pytest.fixture
def sample_alert_data() -> Dict:
    """示例告警数据"""
    return {
        "alert_name": "PodCrashLooping",
        "triggered": True,
        "trigger_time": "2024-01-01 00:00:00",
        "wait_time": 30,
        "alert_details": {
            "labels": {
                "alertname": "PodCrashLooping",
                "severity": "critical"
            }
        },
        "message": "告警在 30 秒后触发"
    }


@pytest.fixture
def sample_chaos_config() -> Dict:
    """示例混沌工程配置"""
    return {
        "namespace": "default",
        "pod_name": "test-pod",
        "duration": "30s",
        "action": "pod-kill"
    }


@pytest.fixture
def prometheus_url() -> str:
    """测试用 Prometheus URL"""
    return "http://localhost:9090"


@pytest.fixture
def k8s_namespace() -> str:
    """测试用 Kubernetes 命名空间"""
    return "default"


# ============================================================================
# Cleanup Fixtures
# ============================================================================

@pytest.fixture(autouse=True)
def reset_logging():
    """每个测试后重置日志配置"""
    import logging
    yield
    # 清理所有 handlers
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)


# ============================================================================
# Markers
# ============================================================================

def pytest_configure(config):
    """配置 pytest"""
    config.addinivalue_line(
        "markers", "unit: 单元测试"
    )
    config.addinivalue_line(
        "markers", "integration: 集成测试"
    )
    config.addinivalue_line(
        "markers", "slow: 慢速测试"
    )
