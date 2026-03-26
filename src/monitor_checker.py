"""
监控验证模块 - Monitor Checker

功能：
1. 调用 Prometheus HTTP API 查询告警状态
2. 验证预期告警是否触发
3. 记录告警触发时间和详情

作者：应急运维工程师
"""

import time
import logging
import requests
from datetime import datetime
from typing import Dict, List, Optional

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PrometheusClient:
    """Prometheus 客户端"""

    def __init__(self, url: str, username: Optional[str] = None, password: Optional[str] = None):
        """
        初始化 Prometheus 客户端

        参数：
            url: Prometheus 地址（如 http://localhost:9090）
            username: 用户名（可选）
            password: 密码（可选）
        """
        self.url=url.rstrip('/')
        self.auth = (username, password) if username and password else None
        logger.info(f"✓ Prometheus 客户端初始化成功: {self.url}")

    def query_alerts(self) -> List[Dict]:
        """
        查询当前所有活跃的告警

        返回：
            list: 告警列表
        """
        try:
            api_url = f"{self.url}/api/v1/alerts"
            response = requests.get(api_url, auth=self.auth, timeout=10)
            response.raise_for_status()

            data = response.json()
            if data['status'] == 'success':
                alerts = data['data']['alerts']
                logger.info(f"✓ 查询到 {len(alerts)} 个活跃告警")
                return alerts
            else:
                logger.error(f"✗ Prometheus API 返回错误: {data}")
                return []

        except requests.exceptions.RequestException as e:
            logger.error(f"✗ 查询告警失败: {e}")
            return []

    def query_alert_by_name(self, alert_name: str) -> Optional[Dict]:
        """
        查询指定名称的告警

        参数：
            alert_name: 告警名称

        返回：
            dict: 告警详情，如果不存在返回 None
        """
        alerts = self.query_alerts()
        for alert in alerts:
            if alert.get('labels', {}).get('alertname') == alert_name:
                logger.info(f"✓ 找到告警: {alert_name}")
                return alert

        logger.warning(f"⚠ 未找到告警: {alert_name}")
        return None

    def query_metrics(self, query: str) -> Dict:
        """
        执行 PromQL 查询

        参数：
            query: PromQL 查询语句

        返回：
            dict: 查询结果
        """
        try:
            api_url = f"{self.url}/api/v1/query"
            params = {'query': query}
            response = requests.get(api_url, params=params, auth=self.auth, timeout=10)
            response.raise_for_status()

            data = response.json()
            if data['status'] == 'success':
                logger.info(f"✓ PromQL 查询成功: {query}")
                return data['data']
            else:
                logger.error(f"✗ PromQL 查询失败: {data}")
                return {}

        except requests.exceptions.RequestException as e:
            logger.error(f"✗ PromQL 查询失败: {e}")
            return {}

    def query_range(self, query: str, start: float, end: float, step: str = "60s") -> List[Dict]:
        """
        执行 PromQL 范围查询，返回时序趋势数据

        参数：
            query: PromQL 查询语句
            start: 开始时间（Unix 时间戳）
            end:   结束时间（Unix 时间戳）
            step:  步长，如 '15s', '60s', '5m'

        返回：
            list: [{metric: {标签}, values: [[时间戳, 值], ...]}]
        """
        try:
            api_url = f"{self.url}/api/v1/query_range"
            params = {'query': query, 'start': start, 'end': end, 'step': step}
            response = requests.get(api_url, params=params, auth=self.auth, timeout=15)
            response.raise_for_status()

            data = response.json()
            if data['status'] == 'success':
                return data['data'].get('result', [])
            logger.error(f"✗ PromQL 范围查询失败: {data}")
            return []

        except requests.exceptions.RequestException as e:
            logger.error(f"✗ PromQL 范围查询失败: {e}")
            return []


class MonitorChecker:
    """监控验证器"""

    def __init__(self, prometheus_url: str, username: Optional[str] = None, password: Optional[str] = None):
        """
        初始化监控验证器

        参数：
            prometheus_url: Prometheus 地址
            username: 用户名（可选）
            password: 密码（可选）
        """
        self.prometheus = PrometheusClient(prometheus_url, username, password)

    def wait_for_alert(self, alert_name: str, timeout: int = 300, check_interval: int = 10) -> Dict:
        """
        等待指定告警触发

        参数：
            alert_name: 告警名称
            timeout: 超时时间（秒）
            check_interval: 检查间隔（秒）

        返回：
            dict: 验证结果
        """
        result = {
            "alert_name": alert_name,
            "triggered": False,
            "trigger_time": None,
            "wait_time": None,
            "alert_details": None,
            "message": ""
        }

        logger.info(f"开始等待告警触发: {alert_name}")
        logger.info(f"超时时间: {timeout} 秒，检查间隔: {check_interval} 秒")

        start_time = time.time()

        while time.time() - start_time < timeout:
            elapsed = int(time.time() - start_time)
            logger.info(f"⏱ 已等待 {elapsed} 秒，正在检查告警...")

            # 查询告警
            alert = self.prometheus.query_alert_by_name(alert_name)

            if alert:
                # 告警已触发
                wait_time = int(time.time() - start_time)
                result["triggered"] = True
                result["trigger_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                result["wait_time"] = wait_time
                result["alert_details"] = alert
                result["message"] = f"告警在 {wait_time} 秒后触发"

                logger.info(f"✓ 告警已触发！等待时间: {wait_time} 秒")
                logger.info(f"告警详情: {alert.get('labels', {})}")

                return result

            # 等待下一次检查
            time.sleep(check_interval)

        # 超时未触发
        wait_time = int(time.time() - start_time)
        result["wait_time"] = wait_time
        result["message"] = f"告警在 {timeout} 秒内未触发"
        logger.warning(f"⚠ 超时：告警在 {timeout} 秒内未触发")

        return result

    def verify_alert_exists(self, alert_name: str) -> bool:
        """
        验证告警是否存在（立即检查）

        参数：
            alert_name: 告警名称

        返回：
            bool: 是否存在
        """
        alert = self.prometheus.query_alert_by_name(alert_name)
        return alert is not None

    def check_pod_metrics(self, namespace: str, pod_name: str) -> Dict:
        """
        检查 Pod 相关指标

        参数：
            namespace: 命名空间
            pod_name: Pod 名称

        返回：
            dict: 指标数据
        """
        metrics = {}

        # 查询 Pod 重启次数
        query = f'kube_pod_container_status_restarts_total{{namespace="{namespace}", pod=~"{pod_name}.*"}}'
        result = self.prometheus.query_metrics(query)
        if result and result.get('result'):
            metrics['restart_count'] = result['result']

        # 查询 Pod 状态
        query = f'kube_pod_status_phase{{namespace="{namespace}", pod=~"{pod_name}.*"}}'
        result = self.prometheus.query_metrics(query)
        if result and result.get('result'):
            metrics['pod_status'] = result['result']

        return metrics


def main():
    """主函数 - 用于测试"""
    print("=" * 60)
    print("应急演练自动化平台 - 监控验证模块")
    print("=" * 60)
    print()

    # 配置 Prometheus 地址
    print("【配置说明】")
    print("-" * 60)
    print("请配置你的 Prometheus 地址")
    print()

    # 从环境变量读取，如果没有则使用默认值
    import os
    default_url = os.environ.get('PROMETHEUS_URL', 'http://localhost:9090')
    prometheus_url = input(f"Prometheus URL [{default_url}]: ").strip() or default_url
    try:
        # 初始化监控验证器
        checker = MonitorChecker(prometheus_url)

        # 示例 1：查询所有活跃告警
        print()
        print("【示例 1】查询当前所有活跃告警")
        print("-" * 60)
        alerts = checker.prometheus.query_alerts()

        if alerts:
            print(f"找到 {len(alerts)} 个活跃告警：")
            print()
            for i, alert in enumerate(alerts, 1):
                labels = alert.get('labels', {})
                print(f"{i}. 告警名称: {labels.get('alertname', 'N/A')}")
                print(f"   严重级别: {labels.get('severity', 'N/A')}")
                print(f"   状态: {alert.get('state', 'N/A')}")
                print(f"   描述: {alert.get('annotations', {}).get('summary', 'N/A')}")
                print()
        else:
            print("当前没有活跃告警")

        print()
        print("【示例 2】等待指定告警触发")
        print("-" * 60)
        print("输入要监听的告警名称（如 PodCrashLooping）")
        alert_name = input("告警名称: ").strip()

        if alert_name:
            print(f"\n开始监听告警: {alert_name}")
            print("(提示: 按 Ctrl+C 中断)\n")

            result = checker.wait_for_alert(
                alert_name=alert_name,
                timeout=60,  # 演示用，只等待 60 秒
                check_interval=5
            )

            print()
            print("=" * 60)
            print("验证结果")
            print("=" * 60)
            print(f"告警名称: {result['alert_name']}")
            print(f"是否触发: {'✅ 是' if result['triggered'] else '❌ 否'}")
            print(f"等待时间: {result['wait_time']} 秒")
            if result['triggered']:
                print(f"触发时间: {result['trigger_time']}")
            print(f"消息: {result['message']}")

    except KeyboardInterrupt:
        print("\n\n操作已取消")
    except Exception as e:
        logger.error(f"发生错误: {e}")


if __name__ == "__main__":
    main()
