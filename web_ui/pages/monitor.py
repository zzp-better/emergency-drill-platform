"""
监控面板页面模块 - Prometheus 原生趋势图
"""
import streamlit as st
import pandas as pd
import sys
import os
import time as _time
import requests as _req
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

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
            ["最近 15 分钟", "最近 1 小时", "最近 6 小时", "最近 24 小时"],
            index=1,
            key="mon_time_range",
            label_visibility="collapsed",
        )
    with c_ns:
        ns_filter = st.text_input("命名空间过滤", value="", placeholder="命名空间（留空=全部）", key="mon_ns", label_visibility="collapsed")
    with c_pod:
        pod_filter = st.text_input("Pod 过滤", value="", placeholder="Pod 名称（支持正则）", key="mon_pod", label_visibility="collapsed")
    with c_auto:
        auto_refresh = st.selectbox("自动刷新", ["关闭", "5秒", "15秒", "1分钟"], key="mon_auto_refresh", label_visibility="collapsed")
    with c_refresh:
        do_refresh = st.button("🔄", use_container_width=True, key="mon_refresh")

    # 自动刷新逻辑
    if auto_refresh != "关闭":
        refresh_map = {"5秒": 5, "15秒": 15, "1分钟": 60}
        st.rerun()

    # 计算时间范围
    now = _time.time()
    range_map = {
        "最近 15 分钟": (now - 900,  "15s"),
        "最近 1 小时":  (now - 3600, "30s"),
        "最近 6 小时":  (now - 21600,"120s"),
        "最近 24 小时": (now - 86400,"300s"),
    }
    start_ts, step = range_map[time_range]

    # 辅助函数：Prometheus 范围查询 → DataFrame
    def _query_df(query: str, label_key: str = None, value_scale: float = 1.0):
        """执行范围查询，返回以时间为索引的 DataFrame"""
        series_list = prom.prometheus.query_range(query, start_ts, now, step)
        if not series_list:
            return pd.DataFrame()
        dfs = []
        for s in series_list:
            m = s.get('metric', {})
            vals = s.get('values', [])
            if not vals:
                continue
            if label_key and m.get(label_key):
                col = m[label_key]
            elif m.get('pod'):
                col = m['pod']
            elif m.get('__name__'):
                col = m['__name__']
            else:
                col = str(m)[:40]
            timestamps = [datetime.fromtimestamp(float(ts)) for ts, _ in vals]
            values = [float(v) * value_scale for _, v in vals]
            dfs.append(pd.DataFrame({col: values}, index=timestamps))
        if not dfs:
            return pd.DataFrame()
        result = dfs[0]
        for df in dfs[1:]:
            result = result.join(df, how='outer')
        return result

    _prom_url  = prom.prometheus.url
    _prom_auth = prom.prometheus.auth

    def _instant(q):
        """即时查询 /api/v1/query"""
        try:
            r = _req.get(f"{_prom_url}/api/v1/query",
                        params={'query': q}, auth=_prom_auth, timeout=8)
            d = r.json()
            if d.get('status') == 'success':
                return d['data']['result'], None
            return [], d.get('error', f'status={d.get("status")}')
        except Exception as exc:
            return [], str(exc)

    # 自动检测 cAdvisor label 格式
    _pod_chk, _ = _instant('count(container_cpu_usage_seconds_total{namespace!="",pod!=""})')
    if _pod_chk and int(float(_pod_chk[0]['value'][1])) > 0:
        _ns_lbl, _pod_lbl = 'namespace', 'pod'
        _cont_chk, _ = _instant('count(container_cpu_usage_seconds_total{namespace!="",pod!="",container!=""})')
        _cont_lbl = 'container' if (_cont_chk and int(float(_cont_chk[0]['value'][1])) > 0) else None
    else:
        _ns_lbl, _pod_lbl, _cont_lbl = 'namespace', 'pod', None

    # 构建 PromQL 过滤器
    ns_selector  = f'{_ns_lbl}="{ns_filter}"' if ns_filter else f'{_ns_lbl}!=""'
    pod_selector = f'{_pod_lbl}=~"{pod_filter}.*"' if pod_filter else f'{_pod_lbl}!=""'
    if _cont_lbl:
        container_selector = f'{_cont_lbl}!="",{_cont_lbl}!="POD",{ns_selector},{pod_selector}'
    else:
        container_selector = f'{ns_selector},{pod_selector}'

    st.markdown("---")

    # 第一行：告警数 + Pod 重启
    row1_left, row1_right = st.columns(2)

    with row1_left:
        st.subheader("🔔 活跃告警数")
        df_alerts = _query_df('sum(ALERTS{alertstate="firing"}) or vector(0)', label_key="__name__")
        if not df_alerts.empty:
            df_alerts.columns = ["告警数"]
            st.line_chart(df_alerts, use_container_width=True)
        else:
            st.info("暂无数据（Prometheus 未返回该指标）")

    with row1_right:
        st.subheader("🔁 Pod 重启次数（增量）")
        df_restart = _query_df(
            f'sum by (pod) (increase(kube_pod_container_status_restarts_total{{{ns_selector},{pod_selector}}}[1m]))',
        )
        if not df_restart.empty:
            st.line_chart(df_restart, use_container_width=True)
        else:
            st.info("暂无数据（需要 kube-state-metrics）")

    # 第二行：CPU + 内存
    row2_left, row2_right = st.columns(2)

    with row2_left:
        st.subheader("⚡ CPU 使用率（%）")
        df_cpu = _query_df(
            f'sum by ({_pod_lbl}) (rate(container_cpu_usage_seconds_total{{{container_selector}}}[2m]))',
            label_key=_pod_lbl,
            value_scale=100,
        )
        if not df_cpu.empty:
            st.line_chart(df_cpu, use_container_width=True)
        else:
            st.info("暂无数据（需要 cAdvisor / kubelet metrics）")

    with row2_right:
        st.subheader("🧠 内存使用量（MB）")
        df_mem = _query_df(
            f'sum by ({_pod_lbl}) (container_memory_working_set_bytes{{{container_selector}}})',
            label_key=_pod_lbl,
            value_scale=1 / (1024 * 1024),
        )
        if not df_mem.empty:
            st.line_chart(df_mem, use_container_width=True)
        else:
            st.info("暂无数据（需要 cAdvisor / kubelet metrics）")

    # 第三行：网络 + EDAP 自定义指标
    row3_left, row3_right = st.columns(2)

    with row3_left:
        st.subheader("🌐 网络接收流量（KB/s）")
        df_net = _query_df(
            f'sum by ({_pod_lbl}) (rate(container_network_receive_bytes_total{{{ns_selector},{pod_selector}}}[2m]))',
            label_key=_pod_lbl,
            value_scale=1 / 1024,
        )
        if not df_net.empty:
            st.line_chart(df_net, use_container_width=True)
        else:
            st.info("暂无数据（需要 cAdvisor 网络指标）")

    with row3_right:
        st.subheader("🎯 EDAP 演练恢复时间（秒）")
        df_edap = _query_df('edap_recovery_time_seconds', label_key='scenario')
        if not df_edap.empty:
            st.line_chart(df_edap, use_container_width=True)
        else:
            st.info("暂无演练指标\n\n需要在设置中配置 Pushgateway 并完成演练")
