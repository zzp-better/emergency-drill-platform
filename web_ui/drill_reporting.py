"""
演练结果与报告模块
负责演练结果展示、Markdown 报告生成，以及报告元数据解析。
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Optional

import streamlit as st

META_BEGIN = "<!-- EDAP_META"
META_END = "EDAP_META -->"


def render_drill_task_result(task: dict) -> None:
    """渲染演练完成后的结果摘要。"""
    entry = task.get("entry", {})
    result = task.get("result", {})
    alert_verification = task.get("alert_verification")
    params_snapshot = task.get("params_snapshot", {})

    st.markdown("---")
    st.subheader("📊 演练结果")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("场景", entry.get("scenario", "N/A"))
    with col2:
        st.metric("状态", "成功" if result.get("success") else "失败")
    with col3:
        st.metric("耗时", f"{entry.get('duration', 0):.2f} 秒")
    with col4:
        if alert_verification and alert_verification.get("alert_name"):
            alert_status = "已触发" if alert_verification.get("triggered") else "未触发"
            st.metric("告警验证", alert_status)
        else:
            st.metric("告警验证", "未配置")

    st.markdown(
        f"**命名空间**: {entry.get('namespace', '')}  \n"
        f"**Pod 名称**: {entry.get('pod_name', '')}  \n"
        f"**故障类型**: {entry.get('scenario_type', '')}  \n"
        f"**完成时间**: {task.get('end_time_str', '')}"
    )

    if params_snapshot:
        with st.expander("🧾 执行参数"):
            for key, value in _build_param_rows(params_snapshot):
                st.markdown(f"**{key}**: {value}")

    if result.get("recovery_time"):
        st.info(f"📈 Pod 恢复时间: {result['recovery_time']} 秒")

    render_alert_verification(alert_verification)

    if result.get("stdout"):
        with st.expander("📄 脚本输出 (stdout)"):
            st.code(result["stdout"], language="text")
    if result.get("stderr"):
        with st.expander("⚠ 错误输出 (stderr)"):
            st.code(result["stderr"], language="text")
    if result.get("message"):
        st.info(f"💬 消息: {result['message']}")

    report_path = task.get("report_path")
    if report_path:
        st.success(f"📄 已生成演练报告: {os.path.basename(report_path)}")


def render_alert_verification(alert_verification: Optional[dict]) -> None:
    """渲染告警验证结果。"""
    if not alert_verification:
        return

    st.markdown("#### 🔔 告警验证结果")

    if alert_verification.get("triggered"):
        st.success(
            f"✅ 告警 **{alert_verification.get('alert_name', '未知')}** "
            f"在 {alert_verification.get('wait_time', 0)} 秒后触发"
        )
    elif alert_verification.get("status") == "timeout":
        st.warning(
            f"⚠ 告警 **{alert_verification.get('alert_name', '未知')}** "
            f"在 {alert_verification.get('wait_time', 0)} 秒内未触发"
        )
    elif alert_verification.get("status") == "error":
        st.error(f"❌ 告警验证失败: {alert_verification.get('message', '')}")
    elif alert_verification.get("status") == "stopped":
        st.warning("⛔ 告警验证已被停止")
    else:
        st.info(alert_verification.get("message", "未执行告警验证"))

    if alert_verification.get("alert_details"):
        with st.expander("查看告警详情"):
            st.json(alert_verification["alert_details"])


def generate_drill_report(
    scenario,
    namespace,
    pod_name,
    start_time,
    end_time,
    drill_duration,
    result,
    params: Optional[dict] = None,
    alert_verification: Optional[dict] = None,
):
    """生成 Markdown 报告，并嵌入隐藏元数据用于摘要解析。"""
    reports_dir = "reports"
    os.makedirs(reports_dir, exist_ok=True)

    filename = f"drill_report_{start_time.strftime('%Y%m%d_%H%M%S')}.md"
    filepath = os.path.join(reports_dir, filename)

    metadata = _build_report_metadata(
        scenario=scenario,
        namespace=namespace,
        pod_name=pod_name,
        start_time=start_time,
        end_time=end_time,
        drill_duration=drill_duration,
        result=result,
        params=params,
        alert_verification=alert_verification,
        report_path=filepath,
    )

    content = _build_report_markdown(metadata, result)
    with open(filepath, "w", encoding="utf-8") as file:
        file.write(content)

    return filepath


def list_report_summaries(reports_dir: str = "reports") -> list[dict]:
    """列出报告摘要信息，按文件名倒序。"""
    if not os.path.exists(reports_dir):
        return []

    summaries = []
    for report in sorted(os.listdir(reports_dir), reverse=True):
        if not report.endswith(".md"):
            continue
        if ".." in report or "/" in report or "\\" in report:
            continue

        filepath = os.path.join(reports_dir, report)
        abs_reports_dir = os.path.abspath(reports_dir)
        abs_filepath = os.path.abspath(filepath)
        if not abs_filepath.startswith(abs_reports_dir):
            continue

        metadata = extract_report_metadata(filepath) or {}
        summaries.append(
            {
                "file_name": report,
                "path": filepath,
                "metadata": metadata,
                "mtime": os.path.getmtime(filepath),
            }
        )

    return summaries


def extract_report_metadata(filepath: str) -> Optional[dict]:
    """从报告文件中提取隐藏元数据。"""
    try:
        with open(filepath, "r", encoding="utf-8") as file:
            content = file.read()
    except Exception:
        return None

    start_idx = content.find(META_BEGIN)
    end_idx = content.find(META_END)
    if start_idx == -1 or end_idx == -1 or end_idx <= start_idx:
        return None

    raw = content[start_idx + len(META_BEGIN) : end_idx].strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def render_latest_report_summary(
    report_summaries: list[dict], history: list[dict]
) -> None:
    """渲染最近一次演练摘要。"""
    st.subheader("🧾 最近一次演练摘要")

    latest_report = report_summaries[0] if report_summaries else None
    metadata = latest_report.get("metadata", {}) if latest_report else {}
    latest_history = history[0] if history else {}

    if not latest_report and not latest_history:
        st.info("暂无可展示的演练摘要")
        return

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(
            "最近场景",
            metadata.get("scenario_name") or latest_history.get("scenario") or "N/A",
        )
    with col2:
        status = metadata.get("status") or latest_history.get("status") or "N/A"
        st.metric("最近状态", status)
    with col3:
        duration = metadata.get("duration_seconds")
        if duration is None:
            duration = latest_history.get("duration", 0)
        st.metric("最近耗时", f"{float(duration):.2f} 秒" if duration else "N/A")
    with col4:
        alert_status = metadata.get("alert_status")
        if alert_status:
            st.metric("告警结果", alert_status)
        else:
            st.metric("告警结果", "未配置")

    if latest_report:
        st.caption(f"最新报告文件: {latest_report['file_name']}")


def _build_report_metadata(
    scenario,
    namespace,
    pod_name,
    start_time,
    end_time,
    drill_duration,
    result,
    params: Optional[dict],
    alert_verification: Optional[dict],
    report_path: str,
) -> dict:
    alert_status = "未配置"
    if alert_verification:
        if alert_verification.get("triggered"):
            alert_status = "已触发"
        elif alert_verification.get("status") == "timeout":
            alert_status = "未触发"
        elif alert_verification.get("status") == "error":
            alert_status = "验证失败"
        else:
            alert_status = alert_verification.get("status", "已跳过")

    return {
        "scenario_name": scenario["name"],
        "scenario_type": scenario["type"],
        "namespace": namespace,
        "pod_name": pod_name,
        "start_time": start_time.strftime("%Y-%m-%d %H:%M:%S"),
        "end_time": end_time.strftime("%Y-%m-%d %H:%M:%S"),
        "duration_seconds": round(drill_duration, 2),
        "status": "成功" if result.get("success") else "失败",
        "message": result.get("message", ""),
        "recovery_time": result.get("recovery_time"),
        "alert_name": (alert_verification or {}).get("alert_name", ""),
        "alert_status": alert_status,
        "alert_wait_time": (alert_verification or {}).get("wait_time"),
        "report_file": os.path.basename(report_path),
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "params": _sanitize_params_for_report(params or {}),
    }


def _build_report_markdown(metadata: dict, result: dict) -> str:
    params_lines = "\n".join(
        f"- **{key}**: {value}"
        for key, value in _build_param_rows(metadata.get("params", {}))
    )
    if not params_lines:
        params_lines = "- 无额外参数"

    alert_section = _build_alert_section(metadata)
    output_section = _build_script_output_section(result)
    alert_ok = metadata.get("alert_status") in {"未配置", "已触发"}
    if metadata["status"] == "成功" and alert_ok:
        conclusion = "本次演练按预期完成，适合用于演示或预案验证。"
    elif metadata["status"] == "成功":
        conclusion = (
            "故障注入已完成，但告警验证结果未达预期，建议检查告警规则或监控链路。"
        )
    else:
        conclusion = "本次演练未完全成功，建议检查环境配置和目标资源状态。"
    meta_block = f"{META_BEGIN}\n{json.dumps(metadata, ensure_ascii=False, indent=2)}\n{META_END}"

    return f"""{meta_block}

# 应急演练报告

## 基本信息
- **演练场景**: {metadata['scenario_name']}
- **故障类型**: {metadata['scenario_type']}
- **命名空间**: {metadata['namespace']}
- **Pod 名称**: {metadata['pod_name']}
- **开始时间**: {metadata['start_time']}
- **结束时间**: {metadata['end_time']}
- **演练耗时**: {metadata['duration_seconds']:.2f} 秒
- **演练状态**: {'✅ 成功' if metadata['status'] == '成功' else '❌ 失败'}

## 执行参数
{params_lines}

## 演练结果摘要
- **执行结论**: {conclusion}
- **执行消息**: {metadata['message'] or '无'}
- **恢复时间**: {metadata['recovery_time'] or '未记录'}

{alert_section}

{output_section}

## 建议
- 演示前确认目标 Pod 为 Running 状态，且 Prometheus 已连接。
- 如需展示完整闭环，建议保留告警验证并在报告页回看本次结果。

---
*报告生成时间: {metadata['generated_at']}*
"""


def _build_alert_section(metadata: dict) -> str:
    if not metadata.get("alert_name"):
        return """## 告警验证
- 本次未配置告警验证
"""

    wait_time = metadata.get("alert_wait_time")
    wait_text = f"{wait_time} 秒" if wait_time is not None else "未记录"
    return f"""## 告警验证
- **预期告警**: {metadata['alert_name']}
- **验证结果**: {metadata['alert_status']}
- **等待耗时**: {wait_text}
"""


def _build_script_output_section(result: dict) -> str:
    if not result.get("stdout") and not result.get("stderr"):
        return "## 执行输出\n- 无脚本输出"

    lines = ["## 执行输出"]
    if result.get("stdout"):
        lines.append("### stdout")
        lines.append("```text")
        lines.append(result["stdout"].strip() or "(empty)")
        lines.append("```")
    if result.get("stderr"):
        lines.append("### stderr")
        lines.append("```text")
        lines.append(result["stderr"].strip() or "(empty)")
        lines.append("```")
    return "\n".join(lines)


def _sanitize_params_for_report(params: dict) -> dict:
    if not params:
        return {}

    filtered = {}
    for key, value in params.items():
        if key in {"scenario", "script"}:
            continue
        filtered[key] = value
    return filtered


def _build_param_rows(params: dict) -> list[tuple[str, str]]:
    if not params:
        return []

    label_map = {
        "namespace": "命名空间",
        "pod_name": "Pod 名称",
        "timeout": "超时时间",
        "check_interval": "检查间隔",
        "expected_alert_name": "预期告警",
        "alert_timeout": "告警等待超时",
        "alert_check_interval": "告警检查间隔",
        "cpu_workers": "CPU Workers",
        "cpu_load": "CPU 负载",
        "memory_size": "内存大小",
        "memory_workers": "Memory Workers",
        "net_latency": "网络延迟",
        "net_jitter": "网络抖动",
        "disk_path": "磁盘路径",
        "disk_fault_type": "磁盘故障类型",
        "disk_size": "磁盘大小",
        "container": "容器名称",
    }

    rows = []
    for key, value in params.items():
        if value in ("", None, False):
            continue
        label = label_map.get(key, key)
        rows.append((label, str(value)))
    return rows
