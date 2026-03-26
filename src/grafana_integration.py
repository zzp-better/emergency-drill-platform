"""
Grafana 集成模块 - Grafana Integration

功能：
1. 自动创建演练仪表板
2. 管理数据源配置
3. 生成嵌入 URL
4. 推送演练指标到 Prometheus

作者：应急运维工程师
"""

import json
import logging
import requests
import time
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class GrafanaClient:
    """Grafana API 客户端"""

    def __init__(
        self,
        url: str,
        api_key: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None
    ):
        """
        初始化 Grafana 客户端

        参数：
            url: Grafana 地址（如 http://localhost:3000）
            api_key: API Key（推荐）
            username: 用户名（可选）
            password: 密码（可选）
        """
        self.url = url.rstrip('/')
        self.headers = {'Content-Type': 'application/json'}

        if api_key:
            self.headers['Authorization'] = f'Bearer {api_key}'
            self.auth = None
        elif username and password:
            self.auth = (username, password)
        else:
            self.auth = None

        self._test_connection()

    def _test_connection(self) -> bool:
        """测试 Grafana 连接"""
        try:
            response = requests.get(
                f"{self.url}/api/health",
                headers=self.headers,
                auth=self.auth,
                timeout=10
            )
            if response.status_code == 200:
                logger.info(f"✓ Grafana 连接成功: {self.url}")
                return True
            else:
                logger.warning(f"⚠ Grafana 连接异常: HTTP {response.status_code}")
                return False
        except Exception as e:
            logger.warning(f"⚠ Grafana 连接失败: {e}")
            return False

    def get_datasources(self) -> List[Dict]:
        """获取所有数据源"""
        try:
            response = requests.get(
                f"{self.url}/api/datasources",
                headers=self.headers,
                auth=self.auth,
                timeout=10
            )
            response.raise_for_status()
            datasources = response.json()
            logger.info(f"✓ 获取到 {len(datasources)} 个数据源")
            return datasources
        except Exception as e:
            logger.error(f"✗ 获取数据源失败: {e}")
            return []

    def get_datasource_by_name(self, name: str) -> Optional[Dict]:
        """根据名称获取数据源"""
        try:
            response = requests.get(
                f"{self.url}/api/datasources/name/{name}",
                headers=self.headers,
                auth=self.auth,
                timeout=10
            )
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            logger.error(f"✗ 获取数据源失败: {e}")
            return None

    def create_datasource(self, datasource_config: Dict) -> Optional[Dict]:
        """创建数据源"""
        try:
            response = requests.post(
                f"{self.url}/api/datasources",
                headers=self.headers,
                auth=self.auth,
                json=datasource_config,
                timeout=10
            )
            if response.status_code in [200, 201]:
                result = response.json()
                logger.info(f"✓ 数据源创建成功: {datasource_config.get('name')}")
                return result
            else:
                logger.error(f"✗ 创建数据源失败: {response.text}")
                return None
        except Exception as e:
            logger.error(f"✗ 创建数据源失败: {e}")
            return None

    def get_dashboard(self, uid: str) -> Optional[Dict]:
        """获取仪表板"""
        try:
            response = requests.get(
                f"{self.url}/api/dashboards/uid/{uid}",
                headers=self.headers,
                auth=self.auth,
                timeout=10
            )
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            logger.error(f"✗ 获取仪表板失败: {e}")
            return None

    def create_dashboard(self, dashboard: Dict, folder_id: int = 0, overwrite: bool = True) -> Optional[Dict]:
        """创建或更新仪表板"""
        try:
            payload = {
                "dashboard": dashboard,
                "folderId": folder_id,
                "overwrite": overwrite,
                "message": "Updated by EDAP"
            }
            response = requests.post(
                f"{self.url}/api/dashboards/db",
                headers=self.headers,
                auth=self.auth,
                json=payload,
                timeout=30
            )
            if response.status_code in [200, 201]:
                result = response.json()
                logger.info(f"✓ 仪表板创建/更新成功: {dashboard.get('title')}")
                return result
            else:
                logger.error(f"✗ 创建仪表板失败: {response.text}")
                return None
        except Exception as e:
            logger.error(f"✗ 创建仪表板失败: {e}")
            return None

    def delete_dashboard(self, uid: str) -> bool:
        """删除仪表板"""
        try:
            response = requests.delete(
                f"{self.url}/api/dashboards/uid/{uid}",
                headers=self.headers,
                auth=self.auth,
                timeout=10
            )
            if response.status_code == 200:
                logger.info(f"✓ 仪表板删除成功: {uid}")
                return True
            return False
        except Exception as e:
            logger.error(f"✗ 删除仪表板失败: {e}")
            return False

    def get_dashboard_url(self, uid: str, panel_id: Optional[int] = None) -> str:
        """获取仪表板或面板的访问 URL"""
        if panel_id:
            return f"{self.url}/d/{uid}?viewPanel={panel_id}"
        return f"{self.url}/d/{uid}"

    def get_embed_url(self, uid: str, panel_id: Optional[int] = None, theme: str = "light") -> str:
        """获取嵌入 URL（用于 iframe）"""
        base = f"{self.url}/d-solo/{uid}"
        if panel_id:
            return f"{base}?panelId={panel_id}&theme={theme}"
        return f"{base}?theme={theme}"

    def search_dashboards(self, query: str = "") -> List[Dict]:
        """搜索仪表板"""
        try:
            params = {"query": query, "type": "dash-db"}
            response = requests.get(
                f"{self.url}/api/search",
                headers=self.headers,
                auth=self.auth,
                params=params,
                timeout=10
            )
            if response.status_code == 200:
                return response.json()
            return []
        except Exception as e:
            logger.error(f"✗ 搜索仪表板失败: {e}")
            return []

    def create_annotation(
        self,
        text: str,
        tags: List[str] = None,
        time_ms: Optional[int] = None,
        time_end_ms: Optional[int] = None,
        dashboard_uid: Optional[str] = None,
        panel_id: Optional[int] = None
    ) -> Optional[Dict]:
        """创建注释（用于标记演练事件）"""
        try:
            if time_ms is None:
                time_ms = int(time.time() * 1000)

            payload = {
                "text": text,
                "tags": tags or ["edap", "drill"],
                "time": time_ms,
            }

            if time_end_ms:
                payload["timeEnd"] = time_end_ms
                payload["isRegion"] = True

            if dashboard_uid:
                payload["dashboardUID"] = dashboard_uid
            if panel_id:
                payload["panelId"] = panel_id

            response = requests.post(
                f"{self.url}/api/annotations",
                headers=self.headers,
                auth=self.auth,
                json=payload,
                timeout=10
            )
            if response.status_code in [200, 201]:
                result = response.json()
                logger.info(f"✓ 注释创建成功: {text}")
                return result
            else:
                logger.error(f"✗ 创建注释失败: {response.text}")
                return None
        except Exception as e:
            logger.error(f"✗ 创建注释失败: {e}")
            return None

    def get_annotations(
        self,
        start_ms: Optional[int] = None,
        end_ms: Optional[int] = None,
        tags: Optional[List[str]] = None
    ) -> List[Dict]:
        """获取注释列表"""
        try:
            params = {}
            if start_ms:
                params["from"] = start_ms
            if end_ms:
                params["to"] = end_ms
            if tags:
                params["tags"] = ",".join(tags)

            response = requests.get(
                f"{self.url}/api/annotations",
                headers=self.headers,
                auth=self.auth,
                params=params,
                timeout=10
            )
            if response.status_code == 200:
                return response.json()
            return []
        except Exception as e:
            logger.error(f"✗ 获取注释失败: {e}")
            return []


class DrillDashboardManager:
    """演练仪表板管理器"""

    # 仪表板 UID 前缀
    DASHBOARD_UID_PREFIX = "edap-"

    def __init__(self, grafana_client: GrafanaClient, prometheus_datasource: str = "Prometheus"):
        """
        初始化仪表板管理器

        参数：
            grafana_client: Grafana 客户端实例
            prometheus_datasource: Prometheus 数据源名称
        """
        self.client = grafana_client
        self.prometheus_datasource = prometheus_datasource
        self._datasource_id = None

    def _get_prometheus_datasource_uid(self) -> Optional[str]:
        """获取 Prometheus 数据源 UID（字符串）"""
        if self._datasource_id:
            return self._datasource_id

        ds = self.client.get_datasource_by_name(self.prometheus_datasource)
        if ds:
            self._datasource_id = ds.get("uid") or str(ds.get("id"))
            return self._datasource_id

        # 尝试查找任意 Prometheus 数据源
        datasources = self.client.get_datasources()
        for ds in datasources:
            if ds.get("type") == "prometheus":
                self._datasource_id = ds.get("uid") or str(ds.get("id"))
                return self._datasource_id

        logger.warning(f"⚠ 未找到 Prometheus 数据源: {self.prometheus_datasource}")
        return None

    def create_drill_overview_dashboard(self) -> Optional[Dict]:
        """创建演练总览仪表板"""
        datasource_uid = self._get_prometheus_datasource_uid()
        if not datasource_uid:
            logger.error("✗ 无法创建仪表板：缺少 Prometheus 数据源")
            return None

        datasource_ref = {"type": "prometheus", "uid": datasource_uid}

        dashboard = {
            "uid": f"{self.DASHBOARD_UID_PREFIX}overview",
            "title": "EDAP - 演练总览",
            "tags": ["edap", "emergency-drill"],
            "timezone": "browser",
            "refresh": "30s",
            "panels": [
                # 演练统计面板
                {
                    "id": 1,
                    "title": "演练总次数",
                    "type": "stat",
                    "gridPos": {"h": 4, "w": 4, "x": 0, "y": 0},
                    "datasource": datasource_ref,
                    "targets": [{
                        "expr": "count(edap_drill_total)",
                        "refId": "A"
                    }],
                    "options": {
                        "colorMode": "value",
                        "graphMode": "none"
                    },
                    "fieldConfig": {
                        "defaults": {
                            "color": {"mode": "thresholds"},
                            "thresholds": {
                                "mode": "absolute",
                                "steps": [
                                    {"color": "green", "value": None}
                                ]
                            }
                        }
                    }
                },
                # 成功率面板
                {
                    "id": 2,
                    "title": "演练成功率",
                    "type": "gauge",
                    "gridPos": {"h": 4, "w": 4, "x": 4, "y": 0},
                    "datasource": datasource_ref,
                    "targets": [{
                        "expr": "avg(edap_drill_success_ratio) * 100",
                        "refId": "A"
                    }],
                    "fieldConfig": {
                        "defaults": {
                            "unit": "percent",
                            "min": 0,
                            "max": 100,
                            "color": {"mode": "thresholds"},
                            "thresholds": {
                                "mode": "absolute",
                                "steps": [
                                    {"color": "red", "value": None},
                                    {"color": "yellow", "value": 70},
                                    {"color": "green", "value": 90}
                                ]
                            }
                        }
                    }
                },
                # 平均恢复时间
                {
                    "id": 3,
                    "title": "平均恢复时间",
                    "type": "stat",
                    "gridPos": {"h": 4, "w": 4, "x": 8, "y": 0},
                    "datasource": datasource_ref,
                    "targets": [{
                        "expr": "avg(edap_recovery_time_seconds)",
                        "refId": "A"
                    }],
                    "fieldConfig": {
                        "defaults": {
                            "unit": "s",
                            "color": {"mode": "thresholds"},
                            "thresholds": {
                                "mode": "absolute",
                                "steps": [
                                    {"color": "green", "value": None},
                                    {"color": "yellow", "value": 30},
                                    {"color": "red", "value": 60}
                                ]
                            }
                        }
                    }
                },
                # 活跃告警数
                {
                    "id": 4,
                    "title": "当前活跃告警",
                    "type": "stat",
                    "gridPos": {"h": 4, "w": 4, "x": 12, "y": 0},
                    "datasource": datasource_ref,
                    "targets": [{
                        "expr": "count(ALERTS{alertstate=\"firing\"})",
                        "refId": "A"
                    }],
                    "fieldConfig": {
                        "defaults": {
                            "color": {"mode": "thresholds"},
                            "thresholds": {
                                "mode": "absolute",
                                "steps": [
                                    {"color": "green", "value": None},
                                    {"color": "yellow", "value": 1},
                                    {"color": "red", "value": 5}
                                ]
                            }
                        }
                    }
                },
                # 演练趋势图
                {
                    "id": 5,
                    "title": "演练趋势",
                    "type": "timeseries",
                    "gridPos": {"h": 8, "w": 12, "x": 0, "y": 4},
                    "datasource": datasource_ref,
                    "targets": [
                        {
                            "expr": "increase(edap_drill_total[1h])",
                            "legendFormat": "演练次数",
                            "refId": "A"
                        },
                        {
                            "expr": "increase(edap_drill_success_total[1h])",
                            "legendFormat": "成功次数",
                            "refId": "B"
                        }
                    ],
                    "fieldConfig": {
                        "defaults": {
                            "custom": {
                                "lineWidth": 2,
                                "fillOpacity": 10
                            }
                        }
                    }
                },
                # 恢复时间趋势
                {
                    "id": 6,
                    "title": "恢复时间趋势",
                    "type": "timeseries",
                    "gridPos": {"h": 8, "w": 12, "x": 12, "y": 4},
                    "datasource": datasource_ref,
                    "targets": [{
                        "expr": "edap_recovery_time_seconds",
                        "legendFormat": "{{scenario}}",
                        "refId": "A"
                    }],
                    "fieldConfig": {
                        "defaults": {
                            "unit": "s"
                        }
                    }
                },
                # 演练场景分布
                {
                    "id": 7,
                    "title": "演练场景分布",
                    "type": "piechart",
                    "gridPos": {"h": 8, "w": 6, "x": 0, "y": 12},
                    "datasource": datasource_ref,
                    "targets": [{
                        "expr": "sum by (scenario) (edap_drill_total)",
                        "legendFormat": "{{scenario}}",
                        "refId": "A"
                    }]
                },
                # 最近演练记录
                {
                    "id": 8,
                    "title": "最近演练记录",
                    "type": "table",
                    "gridPos": {"h": 8, "w": 18, "x": 6, "y": 12},
                    "datasource": datasource_ref,
                    "targets": [{
                        "expr": "edap_drill_duration_seconds",
                        "format": "table",
                        "instant": True,
                        "refId": "A"
                    }],
                    "transformations": [
                        {
                            "id": "organize",
                            "options": {
                                "excludeByName": {"Time": True, "__name__": True},
                                "indexByName": {"scenario": 0, "status": 1, "Value": 2}
                            }
                        }
                    ]
                }
            ],
            "schemaVersion": 38,
            "version": 1
        }

        result = self.client.create_dashboard(dashboard)
        if result:
            return {
                "uid": dashboard["uid"],
                "title": dashboard["title"],
                "url": self.client.get_dashboard_url(dashboard["uid"])
            }
        return None

    def create_scenario_dashboard(self, scenario_name: str, scenario_config: Dict = None) -> Optional[Dict]:
        """
        创建特定场景的仪表板

        参数：
            scenario_name: 场景名称
            scenario_config: 场景配置
        """
        datasource_uid = self._get_prometheus_datasource_uid()
        if not datasource_uid:
            logger.error("✗ 无法创建仪表板：缺少 Prometheus 数据源")
            return None

        datasource_ref = {"type": "prometheus", "uid": datasource_uid}
        safe_name = scenario_name.lower().replace(" ", "-").replace("_", "-")
        uid = f"{self.DASHBOARD_UID_PREFIX}scenario-{safe_name}"

        dashboard = {
            "uid": uid,
            "title": f"EDAP - {scenario_name} 演练",
            "tags": ["edap", "emergency-drill", scenario_name],
            "timezone": "browser",
            "refresh": "10s",
            "panels": [
                # 场景状态
                {
                    "id": 1,
                    "title": "场景状态",
                    "type": "stat",
                    "gridPos": {"h": 4, "w": 6, "x": 0, "y": 0},
                    "datasource": datasource_ref,
                    "targets": [{
                        "expr": f'edap_drill_status{{scenario="{scenario_name}"}}',
                        "refId": "A"
                    }],
                    "fieldConfig": {
                        "defaults": {
                            "mappings": [
                                {"type": "value", "options": {"0": {"text": "空闲", "color": "gray"}}},
                                {"type": "value", "options": {"1": {"text": "运行中", "color": "blue"}}},
                                {"type": "value", "options": {"2": {"text": "成功", "color": "green"}}},
                                {"type": "value", "options": {"3": {"text": "失败", "color": "red"}}}
                            ]
                        }
                    }
                },
                # 执行次数
                {
                    "id": 2,
                    "title": "执行次数",
                    "type": "stat",
                    "gridPos": {"h": 4, "w": 3, "x": 6, "y": 0},
                    "datasource": datasource_ref,
                    "targets": [{
                        "expr": f'sum(edap_drill_total{{scenario="{scenario_name}"}})',
                        "refId": "A"
                    }]
                },
                # 成功率
                {
                    "id": 3,
                    "title": "成功率",
                    "type": "stat",
                    "gridPos": {"h": 4, "w": 3, "x": 9, "y": 0},
                    "datasource": datasource_ref,
                    "targets": [{
                        "expr": f'avg(edap_drill_success_ratio{{scenario="{scenario_name}"}}) * 100',
                        "refId": "A"
                    }],
                    "fieldConfig": {"defaults": {"unit": "percent"}}
                },
                # 平均恢复时间
                {
                    "id": 4,
                    "title": "平均恢复时间",
                    "type": "stat",
                    "gridPos": {"h": 4, "w": 3, "x": 12, "y": 0},
                    "datasource": datasource_ref,
                    "targets": [{
                        "expr": f'avg(edap_recovery_time_seconds{{scenario="{scenario_name}"}})',
                        "refId": "A"
                    }],
                    "fieldConfig": {"defaults": {"unit": "s"}}
                },
                # 持续时间趋势
                {
                    "id": 5,
                    "title": "演练持续时间趋势",
                    "type": "timeseries",
                    "gridPos": {"h": 8, "w": 12, "x": 0, "y": 4},
                    "datasource": datasource_ref,
                    "targets": [{
                        "expr": f'edap_drill_duration_seconds{{scenario="{scenario_name}"}}',
                        "refId": "A"
                    }],
                    "fieldConfig": {"defaults": {"unit": "s"}}
                },
                # 相关告警
                {
                    "id": 6,
                    "title": "相关告警",
                    "type": "timeseries",
                    "gridPos": {"h": 8, "w": 12, "x": 12, "y": 4},
                    "datasource": datasource_ref,
                    "targets": [{
                        "expr": 'ALERTS{alertstate="firing"}',
                        "refId": "A"
                    }]
                }
            ],
            "schemaVersion": 38,
            "version": 1
        }

        result = self.client.create_dashboard(dashboard)
        if result:
            return {
                "uid": dashboard["uid"],
                "title": dashboard["title"],
                "url": self.client.get_dashboard_url(dashboard["uid"])
            }
        return None

    def get_or_create_dashboard(self, scenario_name: str = None) -> Dict:
        """
        获取或创建仪表板

        参数：
            scenario_name: 场景名称（可选，不提供则返回总览仪表板）
        """
        if scenario_name:
            uid = f"{self.DASHBOARD_UID_PREFIX}scenario-{scenario_name.lower().replace(' ', '-').replace('_', '-')}"
            dashboard = self.client.get_dashboard(uid)
            if dashboard:
                return {
                    "uid": uid,
                    "title": dashboard.get("dashboard", {}).get("title", ""),
                    "url": self.client.get_dashboard_url(uid),
                    "exists": True
                }
            return self.create_scenario_dashboard(scenario_name)
        else:
            uid = f"{self.DASHBOARD_UID_PREFIX}overview"
            dashboard = self.client.get_dashboard(uid)
            if dashboard:
                return {
                    "uid": uid,
                    "title": dashboard.get("dashboard", {}).get("title", ""),
                    "url": self.client.get_dashboard_url(uid),
                    "exists": True
                }
            return self.create_drill_overview_dashboard()


class MetricsPusher:
    """指标推送器 - 将演练指标推送到 Prometheus Pushgateway"""

    def __init__(self, pushgateway_url: str, job_name: str = "edap"):
        """
        初始化指标推送器

        参数：
            pushgateway_url: Pushgateway 地址
            job_name: 任务名称
        """
        self.pushgateway_url = pushgateway_url.rstrip('/')
        self.job_name = job_name

    def push_drill_metrics(
        self,
        scenario: str,
        status: str,
        duration: float,
        recovery_time: float = 0,
        success: bool = True,
        labels: Dict[str, str] = None
    ) -> bool:
        """
        推送演练指标

        参数：
            scenario: 场景名称
            status: 状态
            duration: 持续时间（秒）
            recovery_time: 恢复时间（秒）
            success: 是否成功
            labels: 额外标签
        """
        try:
            # 构建指标数据
            metrics = []

            # 演练总次数
            metrics.append(f'edap_drill_total{{scenario="{scenario}"}} 1')

            # 演练状态 (0=空闲, 1=运行中, 2=成功, 3=失败)
            status_value = 2 if success else 3
            metrics.append(f'edap_drill_status{{scenario="{scenario}"}} {status_value}')

            # 演练持续时间
            metrics.append(f'edap_drill_duration_seconds{{scenario="{scenario}"}} {duration}')

            # 恢复时间
            if recovery_time > 0:
                metrics.append(f'edap_recovery_time_seconds{{scenario="{scenario}"}} {recovery_time}')

            # 成功/失败计数
            if success:
                metrics.append(f'edap_drill_success_total{{scenario="{scenario}"}} 1')
            else:
                metrics.append(f'edap_drill_failure_total{{scenario="{scenario}"}} 1')

            # 成功率
            metrics.append(f'edap_drill_success_ratio{{scenario="{scenario}"}} {"1" if success else "0"}')

            # 添加时间戳
            metrics_text = "\n".join(metrics) + f"\n{int(time.time() * 1000)}"

            # 发送到 Pushgateway
            url = f"{self.pushgateway_url}/metrics/job/{self.job_name}/scenario/{scenario}"
            response = requests.post(url, data=metrics_text, timeout=10)

            if response.status_code in [200, 201, 202]:
                logger.info(f"✓ 指标推送成功: {scenario}")
                return True
            else:
                logger.error(f"✗ 指标推送失败: HTTP {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"✗ 指标推送失败: {e}")
            return False


class GrafanaIntegration:
    """Grafana 集成主类"""

    def __init__(
        self,
        grafana_url: str,
        grafana_api_key: str = None,
        grafana_username: str = None,
        grafana_password: str = None,
        prometheus_datasource: str = "Prometheus",
        pushgateway_url: str = None
    ):
        """
        初始化 Grafana 集成

        参数：
            grafana_url: Grafana 地址
            grafana_api_key: API Key
            grafana_username: 用户名
            grafana_password: 密码
            prometheus_datasource: Prometheus 数据源名称
            pushgateway_url: Pushgateway 地址（可选）
        """
        self.client = GrafanaClient(
            url=grafana_url,
            api_key=grafana_api_key,
            username=grafana_username,
            password=grafana_password
        )

        self.dashboard_manager = DrillDashboardManager(
            grafana_client=self.client,
            prometheus_datasource=prometheus_datasource
        )

        self.metrics_pusher = None
        if pushgateway_url:
            self.metrics_pusher = MetricsPusher(pushgateway_url)

    def setup_dashboards(self) -> Dict[str, Any]:
        """初始化所有仪表板"""
        results = {
            "overview": None,
            "scenarios": [],
            "errors": []
        }

        # 创建总览仪表板
        try:
            overview = self.dashboard_manager.create_drill_overview_dashboard()
            results["overview"] = overview
        except Exception as e:
            results["errors"].append(f"创建总览仪表板失败: {e}")

        return results

    def create_drill_annotation(
        self,
        drill_name: str,
        status: str,
        start_time: datetime,
        end_time: datetime = None,
        scenario: str = None
    ) -> Optional[Dict]:
        """
        创建演练注释

        参数：
            drill_name: 演练名称
            status: 状态
            start_time: 开始时间
            end_time: 结束时间（可选）
            scenario: 场景名称
        """
        tags = ["edap", "drill"]
        if scenario:
            tags.append(scenario)

        text = f"演练: {drill_name}\n状态: {status}"

        start_ms = int(start_time.timestamp() * 1000)
        end_ms = int(end_time.timestamp() * 1000) if end_time else None

        return self.client.create_annotation(
            text=text,
            tags=tags,
            time_ms=start_ms,
            time_end_ms=end_ms
        )

    def get_dashboard_embed_url(
        self,
        scenario_name: str = None,
        panel_id: int = None,
        theme: str = "light"
    ) -> str:
        """
        获取仪表板嵌入 URL

        参数：
            scenario_name: 场景名称（可选）
            panel_id: 面板 ID（可选）
            theme: 主题 (light/dark)
        """
        dashboard_info = self.dashboard_manager.get_or_create_dashboard(scenario_name)
        if dashboard_info:
            return self.client.get_embed_url(dashboard_info["uid"], panel_id, theme)
        return ""

    def push_metrics(self, scenario: str, status: str, duration: float, **kwargs) -> bool:
        """推送演练指标"""
        if self.metrics_pusher:
            return self.metrics_pusher.push_drill_metrics(
                scenario=scenario,
                status=status,
                duration=duration,
                **kwargs
            )
        return False

    def get_dashboard_list(self) -> List[Dict]:
        """获取所有 EDAP 仪表板"""
        dashboards = self.client.search_dashboards(query="EDAP")
        return [
            {
                "uid": d.get("uid"),
                "title": d.get("title"),
                "url": self.client.get_dashboard_url(d.get("uid"))
            }
            for d in dashboards
        ]

    def is_connected(self) -> bool:
        """检查 Grafana 连接状态"""
        return self.client._test_connection()


# 便捷函数
def create_grafana_integration_from_config(config: Dict) -> GrafanaIntegration:
    """
    从配置字典创建 Grafana 集成实例

    参数：
        config: 配置字典，包含:
            - grafana_url: Grafana 地址
            - grafana_api_key: API Key（可选）
            - grafana_username: 用户名（可选）
            - grafana_password: 密码（可选）
            - prometheus_datasource: 数据源名称（可选）
            - pushgateway_url: Pushgateway 地址（可选）
    """
    return GrafanaIntegration(
        grafana_url=config.get("grafana_url", "http://localhost:3000"),
        grafana_api_key=config.get("grafana_api_key"),
        grafana_username=config.get("grafana_username"),
        grafana_password=config.get("grafana_password"),
        prometheus_datasource=config.get("prometheus_datasource", "Prometheus"),
        pushgateway_url=config.get("pushgateway_url")
    )
