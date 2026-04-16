"""
配置模块
包含所有默认配置模板和常量
"""

import os


def _int_from_env(name: str, default: int) -> int:
    """从环境变量读取整数配置，非法值时回退到默认值。"""
    try:
        return int(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


# ════════════════════════════════════════════════════
# 默认配置模板
# ════════════════════════════════════════════════════

DEFAULT_CLUSTER = {
    "connection_type": "kubeconfig",
    "kubeconfig_path": os.environ.get(
        "KUBECONFIG", os.path.expanduser("~/.kube/config")
    ),
    "api_server": "",
    "token": "",
    "ca_cert": "",
    "connected": False,
    "cluster_info": {},
    "profile_name": "",
}

DEFAULT_MONITOR = {
    "prometheus_url": os.environ.get("PROMETHEUS_URL", "http://localhost:9090"),
    "username": "",
    "password": "",
    "profile_name": "",
}

DEFAULT_GRAFANA = {
    "grafana_url": os.environ.get("GRAFANA_URL", "http://localhost:3000"),
    "grafana_api_key": "",
    "grafana_username": "admin",
    "grafana_password": "admin",
    "prometheus_datasource": "Prometheus",
    "pushgateway_url": os.environ.get("PUSHGATEWAY_URL", "http://localhost:9091"),
    "enabled": False,
}

DEFAULT_NOTIFY = {
    "enabled": False,
    "webhook_url": "",
    "events": ["演练完成", "演练失败"],
}

# ════════════════════════════════════════════════════
# 页面配置
# ════════════════════════════════════════════════════

PAGE_CONFIG = {
    "page_title": "应急演练智能平台",
    "page_icon": "🚨",
    "layout": "wide",
    "initial_sidebar_state": "expanded",
}

# ════════════════════════════════════════════════════
# 导航菜单
# ════════════════════════════════════════════════════

NAVIGATION_MENU = [
    "🏠 首页",
    "🗂️ 集群资源",
    "⚡ 故障注入",
    "🔗 故障链",
    "📄 演练报告",
    "📊 监控面板",
    "⚙️ 设置",
]

# ════════════════════════════════════════════════════
# 故障场景映射
# ════════════════════════════════════════════════════

SCENARIO_MAP = {
    "cpu_stress": {"type": "cpu_stress", "name": "CPU 压力测试"},
    "memory_stress": {"type": "memory_stress", "name": "内存压力测试"},
    "network_delay": {"type": "network_delay", "name": "网络延迟"},
    "disk_io": {"type": "disk_io", "name": "磁盘 IO"},
    "pod_crash": {"type": "pod_crash", "name": "Pod 崩溃"},
    "custom_script": {"type": "custom_script", "name": "自定义脚本"},
}

# 需要 Chaos Mesh 的场景类型
CHAOS_MESH_SCENARIOS = {"cpu_stress", "network_delay", "disk_io", "memory_stress"}

# Chaos 类型映射（用于清理资源）
CHAOS_TYPE_MAP = {
    "cpu_stress": "stress",
    "memory_stress": "stress",
    "network_delay": "network_delay",
    "disk_io": "io",
}

# ════════════════════════════════════════════════════
# 故障链 Stage 类型
# ════════════════════════════════════════════════════

STAGE_TYPES = ["fault", "wait", "verify_alert"]
FAULT_SCENARIOS = [
    "cpu_stress",
    "memory_stress",
    "network_delay",
    "disk_io",
    "pod_crash",
    "custom_script",
]

# ════════════════════════════════════════════════════
# Demo 展示配置
# ════════════════════════════════════════════════════

DEMO_ENTRY_PAGES = {
    "fault": "⚡ 故障注入",
    "chain": "🔗 故障链",
    "reports": "📄 演练报告",
    "settings": "⚙️ 设置",
}

DEMO_HOME_ACTIONS = [
    {
        "nav": "fault",
        "icon": "⚡",
        "title": "故障注入",
        "desc": "注入 CPU / 内存 / 网络 / Pod 崩溃故障",
        "color": "#FF4B4B",
        "key": "qa_fault",
    },
    {
        "nav": "chain",
        "icon": "🔗",
        "title": "故障链演练",
        "desc": "多步骤编排，模拟级联故障场景",
        "color": "#FF8C00",
        "key": "qa_chain",
    },
    {
        "nav": "reports",
        "icon": "📄",
        "title": "演练报告",
        "desc": "查看历史演练报告与统计数据",
        "color": "#0068C9",
        "key": "qa_reports",
    },
    {
        "nav": "settings",
        "icon": "⚙️",
        "title": "系统设置",
        "desc": "配置集群连接、监控、通知与定时计划",
        "color": "#21C354",
        "key": "qa_settings",
    },
]

DEMO_FLOW_STEPS = [
    {"title": "连接集群", "detail": "进入设置页确认 Kubernetes 已连接"},
    {"title": "连接监控", "detail": "确认 Prometheus 已接通，故障页可看到实时告警状态"},
    {
        "title": "开始标准演示",
        "detail": "进入故障注入页，直接用预填的演示参数执行一次 drill",
    },
    {"title": "查看结果与报告", "detail": "回看演练结果摘要，再进入报告页展示输出物"},
]

DEMO_SCENARIO_PRIORITY = [
    "pod_crash",
    "cpu_stress",
    "network_delay",
    "memory_stress",
    "disk_io",
]

DEMO_DRILL_DEFAULTS = {
    "namespace": os.environ.get("EDAP_DEMO_NAMESPACE", "default"),
    "pod_name": os.environ.get("EDAP_DEMO_POD", "").strip(),
    "timeout": _int_from_env("EDAP_DEMO_TIMEOUT", 60),
    "check_interval": _int_from_env("EDAP_DEMO_CHECK_INTERVAL", 5),
    "cpu_workers": _int_from_env("EDAP_DEMO_CPU_WORKERS", 2),
    "cpu_load": _int_from_env("EDAP_DEMO_CPU_LOAD", 100),
    "memory_size": os.environ.get("EDAP_DEMO_MEMORY_SIZE", "256Mi"),
    "memory_workers": _int_from_env("EDAP_DEMO_MEMORY_WORKERS", 1),
    "net_latency": os.environ.get("EDAP_DEMO_NET_LATENCY", "100ms"),
    "net_jitter": os.environ.get("EDAP_DEMO_NET_JITTER", "10ms"),
    "disk_path": os.environ.get("EDAP_DEMO_DISK_PATH", "/var/log"),
    "disk_fault_type": os.environ.get("EDAP_DEMO_DISK_FAULT_TYPE", "disk_fill"),
    "disk_size": os.environ.get("EDAP_DEMO_DISK_SIZE", "1Gi"),
}
