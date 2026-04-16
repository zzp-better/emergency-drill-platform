"""
监控面板页面模块 - Prometheus 原生趋势图
"""

import streamlit as st
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from ..monitor_dashboard import (
    AUTO_REFRESH_OPTIONS,
    TIME_RANGE_SETTINGS,
    render_monitor_dashboard,
)
from ..state import init_session_state, get_monitor_checker


def render():
    """监控面板页面 - 原生 Prometheus 趋势图"""
    init_session_state()

    st.title("📊 监控面板")

    prom = get_monitor_checker()
    if prom is None:
        st.warning("⚠ 监控未连接，请先在「⚙️ 设置 → 监控」中配置并连接 Prometheus")
        if st.button("前往设置", key="goto_mon_settings"):
            st.rerun()
        return

    # 工具栏
    c_range, c_ns, c_pod, c_auto, c_refresh = st.columns([2, 2, 2, 1, 1])
    with c_range:
        time_range = st.selectbox(
            "时间范围",
            list(TIME_RANGE_SETTINGS.keys()),
            index=1,
            key="mon_time_range",
            label_visibility="collapsed",
        )
    with c_ns:
        ns_filter = st.text_input(
            "命名空间过滤",
            value="",
            placeholder="命名空间（留空=全部）",
            key="mon_ns",
            label_visibility="collapsed",
        )
    with c_pod:
        pod_filter = st.text_input(
            "Pod 过滤",
            value="",
            placeholder="Pod 名称（支持正则）",
            key="mon_pod",
            label_visibility="collapsed",
        )
    with c_auto:
        auto_refresh = st.selectbox(
            "自动刷新",
            AUTO_REFRESH_OPTIONS,
            key="mon_auto_refresh",
            label_visibility="collapsed",
        )
    with c_refresh:
        st.button("🔄", use_container_width=True, key="mon_refresh")

    render_monitor_dashboard(prom, time_range, ns_filter, pod_filter, auto_refresh)
