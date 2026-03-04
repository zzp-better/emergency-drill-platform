"""
monitor.py 的单元测试
测试 prometheus_client 和 monitor_check 类
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import requests
from datetime import datetime


# 导入要测试的模块
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "python测试"))
from monitor import prometheus_client, monitor_check


@pytest.mark.unit
class TestPrometheusClient:
    """测试 prometheus_client 类"""

    def test_init_without_auth(self):
        """测试不带认证的初始化"""
        client = prometheus_client("http://localhost:9090")
        assert client.url == "http://localhost:9090"
        assert client.auth is None

    def test_init_with_auth(self):
        """测试带认证的初始化"""
        client = prometheus_client(
            "http://localhost:9090",
            username="admin",
            password="secret"
        )
        assert client.url == "http://localhost:9090"
        assert client.auth == ("admin", "secret")

    def test_init_strips_trailing_slash(self):
        """测试初始化时去除尾部斜杠"""
        client = prometheus_client("http://localhost:9090/")
        assert client.url == "http://localhost:9090"

    @patch('monitor.requests.get')
    def test_query_alerts_success(self, mock_get):
        """测试成功查询告警"""
        # 模拟成功响应
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "success",
            "data": {
                "alerts": [
                    {
                        "labels": {
                            "alertname": "TestAlert",
                            "severity": "critical"
                        },
                        "state": "firing"
                    }
                ]
            }
        }
        mock_get.return_value = mock_response

        client = prometheus_client("http://localhost:9090")
        alerts = client.query_alerts()

        assert len(alerts) == 1
        assert alerts[0]["labels"]["alertname"] == "TestAlert"
        mock_get.assert_called_once()

    @patch('monitor.requests.get')
    def test_query_alerts_empty(self, mock_get):
        """测试查询告警为空"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "success",
            "data": {
                "alerts": []
            }
        }
        mock_get.return_value = mock_response

        client = prometheus_client("http://localhost:9090")
        alerts = client.query_alerts()

        assert len(alerts) == 0

    @patch('monitor.requests.get')
    def test_query_alerts_api_error(self, mock_get):
        """测试 API 返回错误状态"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "error",
            "error": "query error"
        }
        mock_get.return_value = mock_response

        client = prometheus_client("http://localhost:9090")
        alerts = client.query_alerts()

        assert alerts == []

    @patch('monitor.requests.get')
    def test_query_alerts_network_error(self, mock_get):
        """测试网络错误"""
        mock_get.side_effect = requests.exceptions.ConnectionError("Connection failed")

        client = prometheus_client("http://localhost:9090")
        alerts = client.query_alerts()

        assert alerts == []

    @patch('monitor.requests.get')
    def test_query_alerts_timeout(self, mock_get):
        """测试超时"""
        mock_get.side_effect = requests.exceptions.Timeout("Request timeout")

        client = prometheus_client("http://localhost:9090")
        alerts = client.query_alerts()

        assert alerts == []

    @patch('monitor.requests.get')
    def test_query_alerts_with_auth(self, mock_get):
        """测试带认证的查询"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "success",
            "data": {"alerts": []}
        }
        mock_get.return_value = mock_response

        client = prometheus_client(
            "http://localhost:9090",
            username="admin",
            password="secret"
        )
        client.query_alerts()

        # 验证调用时传递了认证信息
        call_kwargs = mock_get.call_args[1]
        assert call_kwargs['auth'] == ("admin", "secret")


@pytest.mark.unit
class TestMonitorCheck:
    """测试 monitor_check 类"""

    def test_init(self):
        """测试初始化"""
        with patch.object(prometheus_client, '__init__', return_value=None):
            checker = monitor_check("http://localhost:9090")
            assert checker.prometheus is not None

    @patch('monitor.time.sleep', return_value=None)  # 跳过实际睡眠
    @patch('monitor.time.time')
    def test_wait_for_alert_triggered(self, mock_time, mock_sleep):
        """测试告警触发场景"""
        # 模拟时间流逝
        mock_time.side_effect = [0, 10, 20]  # 开始时间，第一次检查，触发时间

        # 创建 mock prometheus 客户端
        mock_prometheus = Mock()
        mock_alert = {
            "labels": {"alertname": "TestAlert"},
            "state": "firing"
        }
        mock_prometheus.query_alert_by_name.return_value = mock_alert

        checker = monitor_check("http://localhost:9090")
        checker.prometheus = mock_prometheus

        result = checker.wait_for_alert("TestAlert", timeout=60, check_interval=5)

        assert result["triggered"] is True
        assert result["alert_name"] == "TestAlert"
        assert result["alert_details"] == mock_alert
        assert "触发" in result["message"]

    @patch('monitor.time.sleep', return_value=None)
    @patch('monitor.time.time')
    def test_wait_for_alert_timeout(self, mock_time, mock_sleep):
        """测试告警超时场景"""
        # 模拟时间流逝超过 timeout
        mock_time.side_effect = [0, 10, 20, 30, 40, 50, 60, 70]

        mock_prometheus = Mock()
        mock_prometheus.query_alert_by_name.return_value = None  # 始终未触发

        checker = monitor_check("http://localhost:9090")
        checker.prometheus = mock_prometheus

        result = checker.wait_for_alert("TestAlert", timeout=60, check_interval=5)

        assert result["triggered"] is False
        assert result["alert_name"] == "TestAlert"
        assert result["alert_details"] is None
        assert "未触发" in result["message"]

    def test_verify_alert_exists_true(self):
        """测试验证告警存在"""
        mock_prometheus = Mock()
        mock_prometheus.query_alert_by_name.return_value = {"labels": {"alertname": "TestAlert"}}

        checker = monitor_check("http://localhost:9090")
        checker.prometheus = mock_prometheus

        result = checker.verify_alert_exists("TestAlert")
        assert result is True

    def test_verify_alert_exists_false(self):
        """测试验证告警不存在"""
        mock_prometheus = Mock()
        mock_prometheus.query_alert_by_name.return_value = None

        checker = monitor_check("http://localhost:9090")
        checker.prometheus = mock_prometheus

        result = checker.verify_alert_exists("TestAlert")
        assert result is False


@pytest.mark.unit
class TestMonitorCheckEdgeCases:
    """测试边界情况"""

    @patch('monitor.time.sleep', return_value=None)
    @patch('monitor.time.time')
    def test_wait_for_alert_immediate_trigger(self, mock_time, mock_sleep):
        """测试立即触发的告警"""
        mock_time.side_effect = [0, 0]  # 立即触发

        mock_prometheus = Mock()
        mock_prometheus.query_alert_by_name.return_value = {"labels": {"alertname": "TestAlert"}}

        checker = monitor_check("http://localhost:9090")
        checker.prometheus = mock_prometheus

        result = checker.wait_for_alert("TestAlert", timeout=60, check_interval=5)

        assert result["triggered"] is True
        assert result["wait_time"] == 0

    def test_empty_url(self):
        """测试空 URL"""
        with pytest.raises(Exception):
            client = prometheus_client("")

    @patch('monitor.requests.get')
    def test_malformed_response(self, mock_get):
        """测试格式错误的响应"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"invalid": "structure"}
        mock_get.return_value = mock_response

        client = prometheus_client("http://localhost:9090")

        # 应该返回空列表而不是崩溃
        with pytest.raises(KeyError):
            client.query_alerts()
