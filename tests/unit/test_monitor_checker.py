"""
monitor_checker.py 的单元测试
测试 MonitorChecker 类
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import time


# 导入要测试的模块
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "emergency-drill-platform" / "src"))
from monitor_checker import MonitorChecker


@pytest.mark.unit
class TestMonitorCheckerInit:
    """测试 MonitorChecker 初始化"""

    def test_init_without_auth(self):
        """测试不带认证的初始化"""
        checker = MonitorChecker("http://localhost:9090")
        assert checker.prometheus_url == "http://localhost:9090"
        assert checker.auth is None

    def test_init_with_auth(self):
        """测试带认证的初始化"""
        checker = MonitorChecker(
            "http://localhost:9090",
            username="admin",
            password="secret"
        )
        assert checker.prometheus_url == "http://localhost:9090"
        assert checker.auth == ("admin", "secret")

    def test_init_strips_trailing_slash(self):
        """测试初始化时去除尾部斜杠"""
        checker = MonitorChecker("http://localhost:9090/")
        assert checker.prometheus_url == "http://localhost:9090"


@pytest.mark.unit
class TestMonitorCheckerQueryAlerts:
    """测试查询告警功能"""

    @patch('monitor_checker.requests.get')
    def test_query_alerts_success(self, mock_get):
        """测试成功查询告警"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "success",
            "data": {
                "alerts": [
                    {
                        "labels": {
                            "alertname": "HighCPU",
                            "severity": "warning"
                        },
                        "state": "firing"
                    }
                ]
            }
        }
        mock_get.return_value = mock_response

        checker = MonitorChecker("http://localhost:9090")
        alerts = checker.query_alerts()

        assert len(alerts) == 1
        assert alerts[0]["labels"]["alertname"] == "HighCPU"

    @patch('monitor_checker.requests.get')
    def test_query_alerts_empty(self, mock_get):
        """测试查询告警为空"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "success",
            "data": {"alerts": []}
        }
        mock_get.return_value = mock_response

        checker = MonitorChecker("http://localhost:9090")
        alerts = checker.query_alerts()

        assert len(alerts) == 0

    @patch('monitor_checker.requests.get')
    def test_query_alerts_connection_error(self, mock_get):
        """测试连接错误"""
        mock_get.side_effect = Exception("Connection failed")

        checker = MonitorChecker("http://localhost:9090")
        alerts = checker.query_alerts()

        assert alerts == []


@pytest.mark.unit
class TestMonitorCheckerQueryAlertByName:
    """测试按名称查询告警"""

    @patch('monitor_checker.requests.get')
    def test_query_alert_by_name_found(self, mock_get):
        """测试找到指定告警"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "success",
            "data": {
                "alerts": [
                    {
                        "labels": {"alertname": "TargetAlert"},
                        "state": "firing"
                    },
                    {
                        "labels": {"alertname": "OtherAlert"},
                        "state": "firing"
                    }
                ]
            }
        }
        mock_get.return_value = mock_response

        checker = MonitorChecker("http://localhost:9090")
        alert = checker.query_alert_by_name("TargetAlert")

        assert alert is not None
        assert alert["labels"]["alertname"] == "TargetAlert"

    @patch('monitor_checker.requests.get')
    def test_query_alert_by_name_not_found(self, mock_get):
        """测试未找到指定告警"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "success",
            "data": {
                "alerts": [
                    {
                        "labels": {"alertname": "OtherAlert"},
                        "state": "firing"
                    }
                ]
            }
        }
        mock_get.return_value = mock_response

        checker = MonitorChecker("http://localhost:9090")
        alert = checker.query_alert_by_name("NonExistentAlert")

        assert alert is None


@pytest.mark.unit
class TestMonitorCheckerWaitForAlert:
    """测试等待告警触发"""

    @patch('monitor_checker.time.sleep', return_value=None)
    @patch('monitor_checker.time.time')
    @patch.object(MonitorChecker, 'query_alert_by_name')
    def test_wait_for_alert_triggered(self, mock_query, mock_time, mock_sleep):
        """测试告警触发"""
        # 模拟时间流逝
        mock_time.side_effect = [0, 5, 10]

        # 第一次查询返回 None，第二次返回告警
        mock_query.side_effect = [
            None,
            {"labels": {"alertname": "TestAlert"}, "state": "firing"}
        ]

        checker = MonitorChecker("http://localhost:9090")
        result = checker.wait_for_alert("TestAlert", timeout=60, check_interval=5)

        assert result["triggered"] is True
        assert result["alert_name"] == "TestAlert"
        assert result["alert_details"] is not None

    @patch('monitor_checker.time.sleep', return_value=None)
    @patch('monitor_checker.time.time')
    @patch.object(MonitorChecker, 'query_alert_by_name')
    def test_wait_for_alert_timeout(self, mock_query, mock_time, mock_sleep):
        """测试等待超时"""
        # 模拟时间流逝超过 timeout
        mock_time.side_effect = [0, 10, 20, 30, 40, 50, 60, 70]
        mock_query.return_value = None  # 始终未触发

        checker = MonitorChecker("http://localhost:9090")
        result = checker.wait_for_alert("TestAlert", timeout=60, check_interval=5)

        assert result["triggered"] is False
        assert result["alert_name"] == "TestAlert"
        assert "未触发" in result["message"]


@pytest.mark.unit
class TestMonitorCheckerVerifyAlert:
    """测试验证告警"""

    @patch.object(MonitorChecker, 'query_alert_by_name')
    def test_verify_alert_exists_true(self, mock_query):
        """测试告警存在"""
        mock_query.return_value = {"labels": {"alertname": "TestAlert"}}

        checker = MonitorChecker("http://localhost:9090")
        result = checker.verify_alert_exists("TestAlert")

        assert result is True

    @patch.object(MonitorChecker, 'query_alert_by_name')
    def test_verify_alert_exists_false(self, mock_query):
        """测试告警不存在"""
        mock_query.return_value = None

        checker = MonitorChecker("http://localhost:9090")
        result = checker.verify_alert_exists("TestAlert")

        assert result is False


@pytest.mark.unit
class TestMonitorCheckerQueryMetrics:
    """测试查询指标"""

    @patch('monitor_checker.requests.get')
    def test_query_metrics_success(self, mock_get):
        """测试成功查询指标"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "success",
            "data": {
                "resultType": "vector",
                "result": [
                    {
                        "metric": {"__name__": "up", "job": "test"},
                        "value": [1704067200, "1"]
                    }
                ]
            }
        }
        mock_get.return_value = mock_response

        checker = MonitorChecker("http://localhost:9090")
        result = checker.query_metrics("up")

        assert result is not None
        assert result["status"] == "success"
        assert len(result["data"]["result"]) == 1

    @patch('monitor_checker.requests.get')
    def test_query_metrics_error(self, mock_get):
        """测试查询指标错误"""
        mock_get.side_effect = Exception("Query failed")

        checker = MonitorChecker("http://localhost:9090")
        result = checker.query_metrics("invalid_query")

        assert result is None


@pytest.mark.unit
class TestMonitorCheckerEdgeCases:
    """测试边界情况"""

    def test_empty_prometheus_url(self):
        """测试空 Prometheus URL"""
        with pytest.raises(Exception):
            checker = MonitorChecker("")

    @patch('monitor_checker.time.sleep', return_value=None)
    @patch('monitor_checker.time.time')
    @patch.object(MonitorChecker, 'query_alert_by_name')
    def test_wait_for_alert_immediate_trigger(self, mock_query, mock_time, mock_sleep):
        """测试立即触发"""
        mock_time.side_effect = [0, 0]
        mock_query.return_value = {"labels": {"alertname": "TestAlert"}}

        checker = MonitorChecker("http://localhost:9090")
        result = checker.wait_for_alert("TestAlert", timeout=60, check_interval=5)

        assert result["triggered"] is True
        assert result["wait_time"] == 0

    @patch.object(MonitorChecker, 'query_alert_by_name')
    def test_verify_alert_with_special_characters(self, mock_query):
        """测试特殊字符的告警名称"""
        mock_query.return_value = {"labels": {"alertname": "Test-Alert_123"}}

        checker = MonitorChecker("http://localhost:9090")
        result = checker.verify_alert_exists("Test-Alert_123")

        assert result is True

    @patch('monitor_checker.requests.get')
    def test_query_alerts_with_auth(self, mock_get):
        """测试带认证的查询"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "success",
            "data": {"alerts": []}
        }
        mock_get.return_value = mock_response

        checker = MonitorChecker(
            "http://localhost:9090",
            username="admin",
            password="secret"
        )
        checker.query_alerts()

        # 验证调用时传递了认证信息
        call_kwargs = mock_get.call_args[1]
        assert call_kwargs['auth'] == ("admin", "secret")
