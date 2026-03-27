"""
状态管理模块
管理全局状态和 Session State
"""

import threading
import streamlit as st


# ════════════════════════════════════════════════════
# 后台演练任务存储（跨 Streamlit rerun 保持任务状态）
# ════════════════════════════════════════════════════

# 演练任务字典：task_id -> {'status': 'running'|'done'|'error', ...}
_drill_tasks: dict = {}
_drill_tasks_lock = threading.Lock()


def get_drill_task(task_id: str) -> dict:
    """获取演练任务状态"""
    with _drill_tasks_lock:
        return _drill_tasks.get(task_id)


def set_drill_task(task_id: str, task_data: dict) -> None:
    """设置演练任务状态"""
    with _drill_tasks_lock:
        _drill_tasks[task_id] = task_data


def remove_drill_task(task_id: str) -> None:
    """删除演练任务"""
    with _drill_tasks_lock:
        _drill_tasks.pop(task_id, None)


def get_all_drill_tasks() -> dict:
    """获取所有演练任务"""
    with _drill_tasks_lock:
        return _drill_tasks.copy()


def get_running_tasks() -> list:
    """获取所有运行中的任务 ID"""
    with _drill_tasks_lock:
        return [tid for tid, t in _drill_tasks.items() if t.get('status') == 'running']


def send_stop_signal(task_id: str) -> None:
    """发送停止信号给指定任务"""
    with _drill_tasks_lock:
        if task_id in _drill_tasks:
            _drill_tasks[task_id]['stop_signal'] = True


def check_stop_signal(task_id: str) -> bool:
    """检查任务是否收到停止信号"""
    with _drill_tasks_lock:
        task = _drill_tasks.get(task_id)
        return task.get('stop_signal', False) if task else False


# ════════════════════════════════════════════════════
# Session State 初始化
# ════════════════════════════════════════════════════

def init_session_state():
    """初始化 Streamlit Session State"""
    import sys
    import os
    
    # 添加 src 目录到 Python 路径
    src_path = os.path.join(os.path.dirname(__file__), '..', 'src')
    if src_path not in sys.path:
        sys.path.insert(0, src_path)
    
    import db
    from .config import DEFAULT_CLUSTER, DEFAULT_MONITOR, DEFAULT_GRAFANA, DEFAULT_NOTIFY
    
    if 'drill_history' not in st.session_state:
        st.session_state.drill_history = db.load_drill_history()

    if 'current_drill' not in st.session_state:
        st.session_state.current_drill = None

    if 'chaos_injector' not in st.session_state:
        st.session_state.chaos_injector = None

    if 'monitor_checker' not in st.session_state:
        st.session_state.monitor_checker = None

    if 'cluster_config' not in st.session_state:
        saved = db.get_default_k8s_profile()
        st.session_state.cluster_config = {**DEFAULT_CLUSTER, **(saved or {})}

    if 'monitor_config' not in st.session_state:
        saved_mon = db.get_default_monitor_profile()
        st.session_state.monitor_config = {**DEFAULT_MONITOR, **(saved_mon or {})}

    if 'cluster_resources' not in st.session_state:
        st.session_state.cluster_resources = {'namespaces': [], 'pods': [], 'deployments': []}

    if 'grafana_config' not in st.session_state:
        st.session_state.grafana_config = {**DEFAULT_GRAFANA}

    if 'grafana_integration' not in st.session_state:
        st.session_state.grafana_integration = None

    if 'fi_pod_list' not in st.session_state:
        st.session_state.fi_pod_list = []

    if 'fi_pod_ns' not in st.session_state:
        st.session_state.fi_pod_ns = ''

    if 'notify_config' not in st.session_state:
        st.session_state.notify_config = DEFAULT_NOTIFY.copy()

    if 'fi_health_check_results' not in st.session_state:
        st.session_state.fi_health_check_results = None

    if 'fi_pending_drill_params' not in st.session_state:
        st.session_state.fi_pending_drill_params = None

    if 'drill_task_id' not in st.session_state:
        st.session_state.drill_task_id = None

    if 'drill_in_progress' not in st.session_state:
        st.session_state.drill_in_progress = False

    if 'auto_connect_done' not in st.session_state:
        st.session_state.auto_connect_done = False


# ════════════════════════════════════════════════════
# Session State 访问器
# ════════════════════════════════════════════════════

def get_chaos_injector():
    """获取故障注入器实例"""
    return st.session_state.chaos_injector


def set_chaos_injector(injector):
    """设置故障注入器实例"""
    st.session_state.chaos_injector = injector


def get_monitor_checker():
    """获取监控验证器实例"""
    return st.session_state.monitor_checker


def set_monitor_checker(checker):
    """设置监控验证器实例"""
    st.session_state.monitor_checker = checker


def get_cluster_config():
    """获取集群配置"""
    return st.session_state.cluster_config


def set_cluster_config(config: dict):
    """设置集群配置"""
    st.session_state.cluster_config = config


def get_monitor_config():
    """获取监控配置"""
    return st.session_state.monitor_config


def set_monitor_config(config: dict):
    """设置监控配置"""
    st.session_state.monitor_config = config


def get_grafana_config():
    """获取 Grafana 配置"""
    return st.session_state.grafana_config


def set_grafana_config(config: dict):
    """设置 Grafana 配置"""
    st.session_state.grafana_config = config


def is_drill_in_progress() -> bool:
    """检查是否有演练进行中"""
    return st.session_state.drill_in_progress


def set_drill_in_progress(status: bool):
    """设置演练进行中状态"""
    st.session_state.drill_in_progress = status


def get_drill_history() -> list:
    """获取演练历史"""
    return st.session_state.drill_history


def add_drill_history(record: dict):
    """添加演练记录"""
    st.session_state.drill_history.append(record)


def refresh_drill_history():
    """刷新演练历史（从数据库重新加载）"""
    import db
    st.session_state.drill_history = db.load_drill_history()


def get_drill_tasks() -> dict:
    """获取演练任务字典"""
    return _drill_tasks


def get_drill_tasks_lock() -> threading.Lock:
    """获取演练任务锁"""
    return _drill_tasks_lock


def get_drill_tasks() -> dict:
    """获取演练任务字典"""
    return _drill_tasks


def get_drill_tasks_lock() -> threading.Lock:
    """获取演练任务锁"""
    return _drill_tasks_lock
