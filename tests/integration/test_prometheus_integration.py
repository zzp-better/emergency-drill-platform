"""
集成测试 - Prometheus 监控集成
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import requests


# 导入要测试的模块
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "emergency-drill-platform" / "src"))
from monitor_checker import MonitorChecker


@pytest.mark.integration
@pytest.mark.prometheus
class TestPrometheusIntegration:
    """Prometheus 集成测试"""

    @patch('monitor_checker.requests.get')
    def test_prometheus_api_connectivity(self, mock_get):
        """测试 Prometheus API 连接性"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "success",
            "data": {"alerts": []}
        }
        mock_get.return_value = mock_response

        monitor = MonitorChecker("http://localhost:9090")
        alerts = monitor.query_alerts()

        assert isinstance(alerts, list)
        mock_get.assert_called_once()

    @patch('monitor_checker.requests.get')
    def test_prometheus_query_with_filters(self, mock_get):
        """测试带过滤条件的 Prometheus 查询"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "success",
            "data": {
                "alerts": [
                    {
                        "labels": {
                            "alertname": "HighCPU",
                            "severity": "warning",
                            "namespace": "production"
                        },
                        "state": "firing"
                    },
                    {
                        "labels": {
                            "alertname": "HighMemory",
                            "severity": "critical",
                            "namespace": "production"
                        },
                        "state": "firing"
                    }
                ]
            }
        }
        mock_get.return_value = mock_response

        monitor = MonitorChecker("http://localhost:9090")
        alerts = monitor.query_alerts()

        # 验证可以过滤特定告警
        critical_alerts = [a for a in alerts if a["labels"]["severity"] == "critical"]
        assert len(critical_alerts) == 1
        assert critical_alerts[0]["labels"]["alertname"] == "HighMemory"

    @patch('monitor_checker.requests.get')
    def test_prometheus_metrics_query(self, mock_get):
        """测试 Prometheus 指标查询"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "success",
            "data": {
                "resultType": "vector",
                "result": [
                    {
                        "metric": {
                            "__name__": "container_cpu_usage_seconds_total",
                            "pod": "test-pod"
                        },
                        "value": [1704067200, "0.5"]
                    }
                ]
            }
        }
        mock_get.return_value = mock_response

        monitor = MonitorChecker("http://localhost:9090")
        result = monitor.query_metrics('container_cpu_usage_seconds_total{pod="test-pod"}')

        assert result is not None
        assert result["status"] == "success"
        assert len(result["data"]["result"]) == 1

    @patch('monitor_checker.requests.get')
    def test_prometheus_alert_state_transitions(self, mock_get):
        """测试告警状态转换"""
        # 模拟告警从 pending 到 firing 的转换
        responses = [
            {
                "status": "success",
                "data": {
                    "alerts": [
                        {
                            "labels": {"alertname": "TestAlert"},
                            "state": "pending"
                        }
                    ]
                }
            },
            {
                "status": "success",
                "data": {
                    "alerts": [
                        {
                            "labels": {"alertname": "TestAlert"},
                            "state": "firing"
                        }
                    ]
                }
            }
        ]

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.side_effect = responses
        mock_get.return_value = mock_response

        monitor = MonitorChecker("http://localhost:9090")

        # 第一次查询 - pending
        alerts1 = monitor.query_alerts()
        assert alerts1[0]["state"] == "pending"

        # 第二次查询 - firing
        alerts2 = monitor.query_alerts()
        assert alerts2[0]["state"] == "firing"

    @patch('monitor_checker.requests.get')
    def test_prometheus_authentication(self, mock_get):
        """测试 Prometheus 认证"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "success",
            "data": {"alerts": []}
        }
        mock_get.return_value = mock_response

        monitor = MonitorChecker(
            "http://localhost:9090",
            username="admin",
            password="secret"
        )
        monitor.query_alerts()

        # 验证认证信息被传递
        call_kwargs = mock_get.call_args[1]
        assert call_kwargs['auth'] == ("admin", "secret")

    @patch('monitor_checker.requests.get')
    def test_prometheus_timeout_handling(self, mock_get):
        """测试 Prometheus 超时处理"""
        mock_get.side_effect = requests.exceptions.Timeout("Request timeout")

        monitor = MonitorChecker("http://localhost:9090")
        alerts = monitor.query_alerts()

        # 应该返回空列表而不是抛出异常
        assert alerts == []

    @patch('monitor_checker.requests.get')
    def test_prometheus_retry_on_failure(self, mock_get):
        """测试失败重试"""
        # 第一次失败，第二次成功
        mock_get.side_effect = [
            requests.exceptions.ConnectionError("Connection failed"),
            Mock(
                status_code=200,
                json=lambda: {
                    "status": "success",
                    "data": {"alerts": []}
                }
            )
        ]

        monitor = MonitorChecker("http://localhost:9090")

        # 第一次调用失败
        alerts1 = monitor.query_alerts()
        assert alerts1 == []

        # 第二次调用成功
        alerts2 = monitor.query_alerts()
        assert isinstance(alerts2, list)


@pytest.mark.integration
@pytest.mark.prometheus
class TestPrometheusAlertRules:
    """Prometheus 告警规则测试"""

    @patch('monitor_checker.requests.get')
    def test_alert_with_multiple_labels(self, mock_get):
        """测试多标签告警"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "success",
            "data": {
                "alerts": [
                    {
                        "labels": {
                            "alertname": "PodDown",
                            "severity": "critical",
                            "namespace": "production",
                            "pod": "api-server-1",
                            "team": "backend"
                        },
                        "annotations": {
                            "summary": "Pod is down",
                            "description": "Pod api-server-1 has been down for 5 minutes"
                        },
                        "state": "firing"
                    }
                ]
            }
        }
        mock_get.return_value = mock_response

        monitor = MonitorChecker("http://localhost:9090")
        alerts = monitor.query_alerts()

        assert len(alerts) == 1
        alert = alerts[0]
        assert alert["labels"]["alertname"] == "PodDown"
        assert alert["labels"]["team"] == "backend"
        assert "summary" in alert["annotations"]

    @patch('monitor_checker.requests.get')
    def test_alert_grouping(self, mock_get):
        """测试告警分组"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "success",
            "data": {
                "alerts": [
                    {
                        "labels": {
                            "alertname": "HighCPU",
                            "severity": "warning",
                            "pod": "pod-1"
                        },
                        "state": "firing"
                    },
                    {
                        "labels": {
                            "alertname": "HighCPU",
                            "severity": "warning",
                            "pod": "pod-2"
                        },
                        "state": "firing"
                    },
                    {
                        "labels": {
                            "alertname": "HighMemory",
                            "severity": "critical",
                            "pod": "pod-3"
                        },
                        "state": "firing"
                    }
                ]
            }
        }
        mock_get.return_value = mock_response

        monitor = MonitorChecker("http://localhost:9090")
        alerts = monitor.query_alerts()

        # 按告警名称分组
        grouped = {}
        for alert in alerts:
            name = alert["labels"]["alertname"]
            if name not in grouped:
                grouped[name] = []
            grouped[name].append(alert)

        assert len(grouped["HighCPU"]) == 2
        assert len(grouped["HighMemory"]) == 1
