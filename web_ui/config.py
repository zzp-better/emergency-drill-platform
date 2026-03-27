"""
配置模块
包含所有默认配置模板和常量
"""

import os

# ════════════════════════════════════════════════════
# 默认配置模板
# ════════════════════════════════════════════════════

DEFAULT_CLUSTER = {
    'connection_type': 'kubeconfig',
    'kubeconfig_path': os.environ.get('KUBECONFIG', os.path.expanduser('~/.kube/config')),
    'api_server': '',
    'token': '',
    'ca_cert': '',
    'connected': False,
    'cluster_info': {},
    'profile_name': '',
}

DEFAULT_MONITOR = {
    'prometheus_url': os.environ.get('PROMETHEUS_URL', 'http://localhost:9090'),
    'username': '',
    'password': '',
    'profile_name': '',
}

DEFAULT_GRAFANA = {
    'grafana_url': os.environ.get('GRAFANA_URL', 'http://localhost:3000'),
    'grafana_api_key': '',
    'grafana_username': 'admin',
    'grafana_password': 'admin',
    'prometheus_datasource': 'Prometheus',
    'pushgateway_url': os.environ.get('PUSHGATEWAY_URL', 'http://localhost:9091'),
    'enabled': False,
}

DEFAULT_NOTIFY = {
    'enabled': False,
    'webhook_url': '',
    'events': ['演练完成', '演练失败'],
}

# ════════════════════════════════════════════════════
# 页面配置
# ════════════════════════════════════════════════════

PAGE_CONFIG = {
    'page_title': '应急演练智能平台',
    'page_icon': '🚨',
    'layout': 'wide',
    'initial_sidebar_state': 'expanded'
}

# ════════════════════════════════════════════════════
# 导航菜单
# ════════════════════════════════════════════════════

NAVIGATION_MENU = [
    '🏠 首页',
    '🗂️ 集群资源',
    '⚡ 故障注入',
    '🔗 故障链',
    '📄 演练报告',
    '📊 监控面板',
    '⚙️ 设置'
]

# ════════════════════════════════════════════════════
# 故障场景映射
# ════════════════════════════════════════════════════

SCENARIO_MAP = {
    'cpu_stress': {'type': 'cpu_stress', 'name': 'CPU 压力测试'},
    'memory_stress': {'type': 'memory_stress', 'name': '内存压力测试'},
    'network_delay': {'type': 'network_delay', 'name': '网络延迟'},
    'disk_io': {'type': 'disk_io', 'name': '磁盘 IO'},
    'pod_crash': {'type': 'pod_crash', 'name': 'Pod 崩溃'},
}

# 需要 Chaos Mesh 的场景类型
CHAOS_MESH_SCENARIOS = {'cpu_stress', 'network_delay', 'disk_io', 'memory_stress'}

# Chaos 类型映射（用于清理资源）
CHAOS_TYPE_MAP = {
    'cpu_stress': 'stress',
    'memory_stress': 'stress',
    'network_delay': 'network_delay',
    'disk_io': 'io',
}

# ════════════════════════════════════════════════════
# 故障链 Stage 类型
# ════════════════════════════════════════════════════

STAGE_TYPES = ['fault', 'wait', 'verify_alert']
FAULT_SCENARIOS = ['cpu_stress', 'memory_stress', 'network_delay', 'disk_io', 'pod_crash']
