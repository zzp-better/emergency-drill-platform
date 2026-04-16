"""
Demo 展示辅助模块
集中管理首页演示入口、环境状态和故障注入页的演示默认参数。
"""

from __future__ import annotations

import streamlit as st

from .config import (
    DEMO_DRILL_DEFAULTS,
    DEMO_ENTRY_PAGES,
    DEMO_FLOW_STEPS,
    DEMO_HOME_ACTIONS,
    DEMO_SCENARIO_PRIORITY,
)

DEMO_MODE_SESSION_KEY = "demo_mode_active"
DEMO_MODE_RESET_KEY = "demo_mode_reset_requested"


def navigate_to_demo_page(nav_key: str) -> None:
    """跳转到指定演示页面。"""
    target_page = DEMO_ENTRY_PAGES.get(nav_key)
    if not target_page:
        return

    st.session_state["_nav_page"] = target_page
    st.rerun()


def activate_standard_demo() -> None:
    """开启标准演示模式并跳转到故障注入页。"""
    st.session_state[DEMO_MODE_SESSION_KEY] = True
    st.session_state[DEMO_MODE_RESET_KEY] = True
    navigate_to_demo_page("fault")


def clear_demo_mode() -> None:
    """关闭演示模式。"""
    st.session_state[DEMO_MODE_SESSION_KEY] = False


def render_demo_mode_banner() -> None:
    """在故障注入页展示演示模式提示。"""
    if not st.session_state.get(DEMO_MODE_SESSION_KEY):
        return

    st.success(
        "🎬 当前处于标准演示模式：已预填推荐场景和参数，适合直接做一次闭环展示。"
    )
    col1, col2 = st.columns(2)
    with col1:
        if st.button(
            "查看演示报告页", key="demo_banner_reports", use_container_width=True
        ):
            navigate_to_demo_page("reports")
    with col2:
        if st.button("退出演示模式", key="demo_banner_exit", use_container_width=True):
            clear_demo_mode()
            st.rerun()


def get_latest_history_entry(history: list[dict]) -> dict | None:
    """获取最近一条演练记录。"""
    if not history:
        return None

    return max(history, key=lambda item: item.get("time", ""))


def render_environment_status_cards(
    history: list[dict],
    cluster_ready: bool,
    monitor_ready: bool,
    running_task_count: int,
) -> None:
    """渲染首页环境状态卡片。"""
    latest_entry = get_latest_history_entry(history)

    st.markdown("### 🧭 环境状态")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("集群连接", "已连接" if cluster_ready else "未连接")
        st.caption(
            "故障注入器已就绪" if cluster_ready else "请先在设置页连接 Kubernetes"
        )

    with col2:
        st.metric("监控连接", "已连接" if monitor_ready else "未连接")
        st.caption(
            "Prometheus 可用于展示告警"
            if monitor_ready
            else "可选，但推荐接通后展示效果更完整"
        )

    with col3:
        st.metric("运行中任务", running_task_count)
        st.caption("首页可直接查看进度并紧急停止")

    with col4:
        latest_status = latest_entry.get("status", "暂无") if latest_entry else "暂无"
        st.metric("最近结果", latest_status)
        if latest_entry:
            st.caption(
                f"{latest_entry.get('scenario', '未知场景')} · {latest_entry.get('time', '')}"
            )
        else:
            st.caption("还没有演练记录")


def render_standard_demo_entry(cluster_ready: bool, monitor_ready: bool) -> None:
    """渲染首页标准演示入口。"""
    ready = cluster_ready and monitor_ready
    status_text = (
        "环境已就绪，可直接开始演示" if ready else "建议先完成环境连接，再开始标准演示"
    )

    st.markdown("### 🎬 标准演示入口")
    st.caption("推荐现场演示路径：故障注入 -> 查看结果 -> 报告展示")
    st.info(status_text)

    col1, col2, col3 = st.columns([1.4, 1, 1])
    with col1:
        if st.button(
            "开始标准演示",
            key="demo_start_fault",
            use_container_width=True,
            type="primary",
        ):
            activate_standard_demo()
    with col2:
        if st.button("查看故障链", key="demo_start_chain", use_container_width=True):
            navigate_to_demo_page("chain")
    with col3:
        if st.button("打开设置", key="demo_open_settings", use_container_width=True):
            navigate_to_demo_page("settings")


def render_demo_flow(cluster_ready: bool, monitor_ready: bool) -> None:
    """渲染推荐演示路径。"""
    st.markdown("### 🪜 推荐演示路径")

    step_states = [
        cluster_ready,
        monitor_ready,
        cluster_ready,
        True,
    ]

    for step, ready in zip(DEMO_FLOW_STEPS, step_states):
        icon = "✅" if ready else "🟡"
        status = "已就绪" if ready else "待完成"
        st.markdown(f"{icon} **{step['title']}** · {status}")
        st.caption(step["detail"])


def render_demo_quick_actions() -> None:
    """渲染首页快速入口卡片。"""
    st.markdown("### 🚀 常用入口")
    cols = st.columns(len(DEMO_HOME_ACTIONS))

    for col, action in zip(cols, DEMO_HOME_ACTIONS):
        with col:
            st.markdown(
                f"""
                <div style="
                    border: 1px solid {action['color']}44;
                    border-left: 4px solid {action['color']};
                    border-radius: 8px;
                    padding: 16px 14px 10px 14px;
                    background: linear-gradient(135deg, {action['color']}0a 0%, transparent 100%);
                    height: 110px;
                    box-sizing: border-box;
                    overflow: hidden;
                ">
                    <div style="font-size:1.6rem; line-height:1;">{action['icon']}</div>
                    <div style="font-weight:700; font-size:1rem; margin: 6px 0 4px;">{action['title']}</div>
                    <div style="font-size:0.75rem; color:#6b7280; line-height:1.4;">{action['desc']}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if st.button("前往 →", key=action["key"], use_container_width=True):
                navigate_to_demo_page(action["nav"])


def seed_fault_injection_demo_state(scenarios: list[dict], injector) -> None:
    """为故障注入页预填演示默认参数。"""
    scenario_options = [f"{item['name']} - {item['description']}" for item in scenarios]
    preferred_label = _get_preferred_scenario_label(scenarios)
    reset_requested = bool(st.session_state.get(DEMO_MODE_RESET_KEY))

    if (
        reset_requested
        or st.session_state.get("fi_scenario_label") not in scenario_options
    ):
        st.session_state.fi_scenario_label = preferred_label

    _set_demo_value("fi_namespace", DEMO_DRILL_DEFAULTS["namespace"], reset_requested)
    _set_demo_value("fi_timeout", DEMO_DRILL_DEFAULTS["timeout"], reset_requested)
    _set_demo_value(
        "fi_check_interval", DEMO_DRILL_DEFAULTS["check_interval"], reset_requested
    )
    _set_demo_value("fi_pod_manual", DEMO_DRILL_DEFAULTS["pod_name"], reset_requested)
    _set_demo_value(
        "fi_cpu_workers", DEMO_DRILL_DEFAULTS["cpu_workers"], reset_requested
    )
    _set_demo_value("fi_cpu_load", DEMO_DRILL_DEFAULTS["cpu_load"], reset_requested)
    _set_demo_value(
        "fi_memory_size", DEMO_DRILL_DEFAULTS["memory_size"], reset_requested
    )
    _set_demo_value(
        "fi_memory_workers", DEMO_DRILL_DEFAULTS["memory_workers"], reset_requested
    )
    _set_demo_value(
        "fi_net_latency", DEMO_DRILL_DEFAULTS["net_latency"], reset_requested
    )
    _set_demo_value("fi_net_jitter", DEMO_DRILL_DEFAULTS["net_jitter"], reset_requested)
    _set_demo_value("fi_disk_path", DEMO_DRILL_DEFAULTS["disk_path"], reset_requested)
    _set_demo_value(
        "fi_disk_fault_type", DEMO_DRILL_DEFAULTS["disk_fault_type"], reset_requested
    )
    _set_demo_value("fi_disk_size", DEMO_DRILL_DEFAULTS["disk_size"], reset_requested)

    if reset_requested:
        st.session_state["_fi_demo_loaded_namespaces"] = []
        st.session_state.pop("fi_pod_select", None)
        st.session_state.pop("_fi_alert_defaults_for", None)
        st.session_state.pop("fi_verify_alert_enabled", None)
        st.session_state.pop("fi_expected_alert_name", None)
        st.session_state.pop("fi_alert_timeout", None)
        st.session_state.pop("fi_alert_check_interval", None)
        st.session_state[DEMO_MODE_RESET_KEY] = False

    namespace = (
        st.session_state.get("fi_namespace") or DEMO_DRILL_DEFAULTS["namespace"]
    ).strip()
    namespace = namespace or DEMO_DRILL_DEFAULTS["namespace"]
    st.session_state.fi_namespace = namespace

    _autoload_demo_pod_options(injector, namespace)

    pod_options = st.session_state.get("fi_pod_list", [])
    pod_namespace = st.session_state.get("fi_pod_ns", "")
    preferred_pod = DEMO_DRILL_DEFAULTS["pod_name"]

    if pod_options and pod_namespace == namespace:
        if st.session_state.get("fi_pod_select") not in pod_options:
            st.session_state.fi_pod_select = (
                preferred_pod if preferred_pod in pod_options else pod_options[0]
            )
        if not st.session_state.get("fi_pod_manual"):
            st.session_state.fi_pod_manual = st.session_state.fi_pod_select


def _get_preferred_scenario_label(scenarios: list[dict]) -> str:
    """根据演示优先级选择默认场景。"""
    for scenario_type in DEMO_SCENARIO_PRIORITY:
        for scenario in scenarios:
            if scenario.get("type") == scenario_type:
                return f"{scenario['name']} - {scenario['description']}"

    fallback = scenarios[0]
    return f"{fallback['name']} - {fallback['description']}"


def _autoload_demo_pod_options(injector, namespace: str) -> None:
    """按命名空间自动加载一次 Pod 选项，降低现场手动输入量。"""
    if injector is None or not namespace:
        return

    loaded_namespaces = st.session_state.setdefault("_fi_demo_loaded_namespaces", [])
    if namespace in loaded_namespaces:
        return

    try:
        pods = injector.list_pods(namespace)
    except Exception:
        pods = []

    loaded_namespaces.append(namespace)

    if not pods:
        return

    st.session_state.fi_pod_list = [pod["name"] for pod in pods]
    st.session_state.fi_pod_ns = namespace


def _set_demo_value(key: str, value, reset_requested: bool) -> None:
    """按需设置或重置演示默认值。"""
    if reset_requested or key not in st.session_state:
        st.session_state[key] = value
