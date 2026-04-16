"""
监控面板辅助模块
封装图表查询逻辑，并使用 Streamlit fragment 控制自动刷新频率。
"""

from __future__ import annotations

import time as _time
from datetime import datetime

import pandas as pd
import requests as _req
import streamlit as st


AUTO_REFRESH_OPTIONS = ["关闭", "5秒", "15秒", "1分钟"]
AUTO_REFRESH_SECONDS = {
    "关闭": None,
    "5秒": 5,
    "15秒": 15,
    "1分钟": 60,
}

TIME_RANGE_SETTINGS = {
    "最近 15 分钟": {"seconds": 900, "step": "15s"},
    "最近 1 小时": {"seconds": 3600, "step": "30s"},
    "最近 6 小时": {"seconds": 21600, "step": "120s"},
    "最近 24 小时": {"seconds": 86400, "step": "300s"},
}


def render_monitor_dashboard(
    prom, time_range: str, ns_filter: str, pod_filter: str, auto_refresh: str
) -> None:
    """渲染监控面板主体。"""
    refresh_seconds = AUTO_REFRESH_SECONDS.get(auto_refresh)

    if refresh_seconds:
        st.caption(f"自动刷新已开启：图表区域每 {refresh_seconds} 秒刷新一次。")
        refreshed_fragment = st.fragment(run_every=refresh_seconds)(
            _render_monitor_charts
        )
        refreshed_fragment(prom, time_range, ns_filter, pod_filter)
        return

    _render_monitor_charts(prom, time_range, ns_filter, pod_filter)


def _render_monitor_charts(
    prom, time_range: str, ns_filter: str, pod_filter: str
) -> None:
    """执行 Prometheus 查询并渲染图表。"""
    now = _time.time()
    range_cfg = TIME_RANGE_SETTINGS[time_range]
    start_ts = now - range_cfg["seconds"]
    step = range_cfg["step"]

    def _query_df(
        query: str, label_key: str = None, value_scale: float = 1.0
    ) -> pd.DataFrame:
        """执行范围查询，返回以时间为索引的 DataFrame。"""
        series_list = prom.prometheus.query_range(query, start_ts, now, step)
        if not series_list:
            return pd.DataFrame()

        frames = []
        for series in series_list:
            metric = series.get("metric", {})
            values = series.get("values", [])
            if not values:
                continue

            if label_key and metric.get(label_key):
                column = metric[label_key]
            elif metric.get("pod"):
                column = metric["pod"]
            elif metric.get("__name__"):
                column = metric["__name__"]
            else:
                column = str(metric)[:40]

            timestamps = [datetime.fromtimestamp(float(ts)) for ts, _ in values]
            points = [float(value) * value_scale for _, value in values]
            frames.append(pd.DataFrame({column: points}, index=timestamps))

        if not frames:
            return pd.DataFrame()

        result = frames[0]
        for frame in frames[1:]:
            result = result.join(frame, how="outer")

        return result

    prom_url = prom.prometheus.url
    prom_auth = prom.prometheus.auth

    def _instant(query: str) -> tuple[list, str | None]:
        """即时查询 /api/v1/query。"""
        try:
            response = _req.get(
                f"{prom_url}/api/v1/query",
                params={"query": query},
                auth=prom_auth,
                timeout=8,
            )
            data = response.json()
            if data.get("status") == "success":
                return data["data"]["result"], None
            return [], data.get("error", f"status={data.get('status')}")
        except Exception as exc:
            return [], str(exc)

    pod_check, _ = _instant(
        'count(container_cpu_usage_seconds_total{namespace!="",pod!=""})'
    )
    if pod_check and int(float(pod_check[0]["value"][1])) > 0:
        namespace_label, pod_label = "namespace", "pod"
        container_check, _ = _instant(
            'count(container_cpu_usage_seconds_total{namespace!="",pod!="",container!=""})'
        )
        container_label = (
            "container"
            if (container_check and int(float(container_check[0]["value"][1])) > 0)
            else None
        )
    else:
        namespace_label, pod_label, container_label = "namespace", "pod", None

    namespace_selector = (
        f'{namespace_label}="{ns_filter}"' if ns_filter else f'{namespace_label}!=""'
    )
    pod_selector = (
        f'{pod_label}=~"{pod_filter}.*"' if pod_filter else f'{pod_label}!=""'
    )
    if container_label:
        container_selector = f'{container_label}!="",{container_label}!="POD",{namespace_selector},{pod_selector}'
    else:
        container_selector = f"{namespace_selector},{pod_selector}"

    st.markdown("---")

    row1_left, row1_right = st.columns(2)
    with row1_left:
        st.subheader("🔔 活跃告警数")
        df_alerts = _query_df(
            'sum(ALERTS{alertstate="firing"}) or vector(0)', label_key="__name__"
        )
        if not df_alerts.empty:
            df_alerts.columns = ["告警数"]
            st.line_chart(df_alerts, use_container_width=True)
        else:
            st.info("暂无数据（Prometheus 未返回该指标）")

    with row1_right:
        st.subheader("🔁 Pod 重启次数（增量）")
        df_restart = _query_df(
            f"sum by (pod) (increase(kube_pod_container_status_restarts_total{{{namespace_selector},{pod_selector}}}[1m]))",
        )
        if not df_restart.empty:
            st.line_chart(df_restart, use_container_width=True)
        else:
            st.info("暂无数据（需要 kube-state-metrics）")

    row2_left, row2_right = st.columns(2)
    with row2_left:
        st.subheader("⚡ CPU 使用率（%）")
        df_cpu = _query_df(
            f"sum by ({pod_label}) (rate(container_cpu_usage_seconds_total{{{container_selector}}}[2m]))",
            label_key=pod_label,
            value_scale=100,
        )
        if not df_cpu.empty:
            st.line_chart(df_cpu, use_container_width=True)
        else:
            st.info("暂无数据（需要 cAdvisor / kubelet metrics）")

    with row2_right:
        st.subheader("🧠 内存使用量（MB）")
        df_mem = _query_df(
            f"sum by ({pod_label}) (container_memory_working_set_bytes{{{container_selector}}})",
            label_key=pod_label,
            value_scale=1 / (1024 * 1024),
        )
        if not df_mem.empty:
            st.line_chart(df_mem, use_container_width=True)
        else:
            st.info("暂无数据（需要 cAdvisor / kubelet metrics）")

    row3_left, row3_right = st.columns(2)
    with row3_left:
        st.subheader("🌐 网络接收流量（KB/s）")
        df_net = _query_df(
            f"sum by ({pod_label}) (rate(container_network_receive_bytes_total{{{namespace_selector},{pod_selector}}}[2m]))",
            label_key=pod_label,
            value_scale=1 / 1024,
        )
        if not df_net.empty:
            st.line_chart(df_net, use_container_width=True)
        else:
            st.info("暂无数据（需要 cAdvisor 网络指标）")

    with row3_right:
        st.subheader("🎯 EDAP 演练恢复时间（秒）")
        df_edap = _query_df("edap_recovery_time_seconds", label_key="scenario")
        if not df_edap.empty:
            st.line_chart(df_edap, use_container_width=True)
        else:
            st.info("暂无演练指标\n\n需要在设置中配置 Pushgateway 并完成演练")
