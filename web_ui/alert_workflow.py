"""
告警验证辅助模块
负责故障注入页的告警配置表单和后台告警等待逻辑。
"""

from __future__ import annotations

import time
from datetime import datetime
from typing import Callable, Optional

import streamlit as st


DEFAULT_ALERT_TIMEOUT = 180
DEFAULT_ALERT_CHECK_INTERVAL = 5


def _find_firing_alert(monitor_checker, alert_name: str) -> dict | None:
    """查找已进入 firing 状态的目标告警。"""
    alerts = monitor_checker.prometheus.query_alerts()
    for alert in alerts:
        if (
            alert.get("labels", {}).get("alertname") == alert_name
            and alert.get("state") == "firing"
        ):
            return alert
    return None


def sync_alert_form_state(scenario: dict) -> None:
    """根据场景默认值刷新告警表单状态。"""
    scenario_key = (
        scenario.get("filename") or scenario.get("type") or scenario.get("name")
    )
    if st.session_state.get("_fi_alert_defaults_for") == scenario_key:
        return

    alert_name = scenario.get("expected_alert_name", "") or ""
    timeout = scenario.get("expected_alert_timeout", DEFAULT_ALERT_TIMEOUT)

    st.session_state["fi_verify_alert_enabled"] = bool(alert_name)
    st.session_state["fi_expected_alert_name"] = alert_name
    st.session_state["fi_alert_timeout"] = int(timeout or DEFAULT_ALERT_TIMEOUT)
    st.session_state["fi_alert_check_interval"] = DEFAULT_ALERT_CHECK_INTERVAL
    st.session_state["_fi_alert_defaults_for"] = scenario_key


def render_alert_expectation_form(monitor_available: bool) -> dict:
    """渲染故障注入页的告警验证配置。"""
    st.markdown("#### 🔔 告警验证（可选）")
    verify_alert = st.checkbox(
        "演练结束后验证 Prometheus 告警",
        key="fi_verify_alert_enabled",
        help="用于 demo 展示“故障注入 -> 告警触发 -> 结果验证”的闭环",
    )

    if not verify_alert:
        return {}

    col1, col2, col3 = st.columns([2.2, 1, 1])
    with col1:
        alert_name = st.text_input(
            "预期告警名称",
            key="fi_expected_alert_name",
            placeholder="例如: PodCrashLooping / HighCPUUsage",
        ).strip()
    with col2:
        alert_timeout = st.number_input(
            "告警等待超时(秒)",
            min_value=10,
            max_value=900,
            key="fi_alert_timeout",
        )
    with col3:
        check_interval = st.number_input(
            "告警检查间隔(秒)",
            min_value=1,
            max_value=60,
            key="fi_alert_check_interval",
        )

    if not monitor_available:
        st.warning("⚠ 当前未连接 Prometheus，开启告警验证后将无法完成闭环校验。")
    elif not alert_name:
        st.warning("⚠ 请填写预期告警名称，否则无法执行告警验证。")

    return {
        "expected_alert_name": alert_name,
        "alert_timeout": int(alert_timeout),
        "alert_check_interval": int(check_interval),
    }


def wait_for_expected_alert(
    monitor_checker,
    alert_name: str,
    timeout: int,
    check_interval: int = DEFAULT_ALERT_CHECK_INTERVAL,
    stop_check: Optional[Callable[[], bool]] = None,
    progress_callback: Optional[Callable[[int, int], None]] = None,
) -> dict:
    """等待指定告警触发，并支持后台进度更新。"""
    result = {
        "alert_name": alert_name,
        "triggered": False,
        "status": "skipped",
        "trigger_time": None,
        "wait_time": 0,
        "alert_details": None,
        "message": "",
    }

    if not alert_name:
        result["message"] = "未配置预期告警，跳过告警验证"
        return result

    if monitor_checker is None:
        result["message"] = "未连接 Prometheus，无法执行告警验证"
        return result

    result["status"] = "running"
    start_time = time.time()

    while True:
        elapsed = int(time.time() - start_time)
        if progress_callback:
            progress_callback(min(elapsed, timeout), timeout)

        if stop_check and stop_check():
            result["status"] = "stopped"
            result["wait_time"] = elapsed
            result["message"] = "用户中断，告警验证已停止"
            return result

        if elapsed >= timeout:
            result["status"] = "timeout"
            result["wait_time"] = timeout
            result["message"] = f"告警 {alert_name} 在 {timeout} 秒内未触发"
            return result

        try:
            alert = _find_firing_alert(monitor_checker, alert_name)
        except Exception as exc:
            result["status"] = "error"
            result["wait_time"] = elapsed
            result["message"] = f"查询告警失败: {exc}"
            return result

        if alert:
            wait_time = int(time.time() - start_time)
            result.update(
                {
                    "triggered": True,
                    "status": "success",
                    "trigger_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "wait_time": wait_time,
                    "alert_details": alert,
                    "message": f"告警 {alert_name} 在 {wait_time} 秒后触发",
                }
            )
            if progress_callback:
                progress_callback(min(wait_time, timeout), timeout)
            return result

        remaining = timeout - elapsed
        time.sleep(min(check_interval, max(1, remaining)))


def summarize_alert_verification(alert_verification: Optional[dict]) -> str:
    """将告警验证结果压缩成简短文案。"""
    if not alert_verification:
        return "未配置告警验证"

    if alert_verification.get("triggered"):
        return f"告警 {alert_verification.get('alert_name', '未知')} 已触发"

    status = alert_verification.get("status")
    if status == "timeout":
        return f"告警 {alert_verification.get('alert_name', '未知')} 未在时限内触发"
    if status == "error":
        return "告警验证失败"
    if status == "stopped":
        return "告警验证被中断"
    return alert_verification.get("message", "未执行告警验证")
