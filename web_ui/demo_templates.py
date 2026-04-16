"""
演示模板模块
提供可直接加载或保存的故障链模板，用于快速展示。
"""

from __future__ import annotations

import copy

import streamlit as st

import db

from .config import DEMO_DRILL_DEFAULTS


def _default_namespace() -> str:
    return DEMO_DRILL_DEFAULTS.get("namespace", "default") or "default"


def _default_pod() -> str:
    return DEMO_DRILL_DEFAULTS.get("pod_name", "").strip() or "请替换为目标Pod"


DEMO_CHAIN_TEMPLATES = [
    {
        "key": "pod_alert_recovery",
        "name": "标准闭环演示链",
        "description": "Pod 崩溃 -> 等待恢复 -> 验证告警，用于展示最完整闭环。",
        "stages": [
            {
                "type": "fault",
                "scenario": "pod_crash",
                "namespace": _default_namespace(),
                "pod_selector": _default_pod(),
                "duration": 10,
            },
            {
                "type": "wait",
                "wait_seconds": 15,
            },
            {
                "type": "verify_alert",
                "alert_name": "PodCrashLooping",
                "expected": "firing",
            },
        ],
    },
    {
        "key": "cpu_alert_demo",
        "name": "CPU 压力告警演示链",
        "description": "CPU 压测 -> 等待负载稳定 -> 验证高 CPU 告警。",
        "stages": [
            {
                "type": "fault",
                "scenario": "cpu_stress",
                "namespace": _default_namespace(),
                "pod_selector": _default_pod(),
                "duration": 60,
                "cpu_workers": DEMO_DRILL_DEFAULTS.get("cpu_workers", 2),
                "cpu_load": DEMO_DRILL_DEFAULTS.get("cpu_load", 100),
            },
            {
                "type": "wait",
                "wait_seconds": 20,
            },
            {
                "type": "verify_alert",
                "alert_name": "HighCPUUsage",
                "expected": "firing",
            },
        ],
    },
]


def render_demo_chain_templates() -> None:
    """渲染故障链模板入口。"""
    st.markdown("### 🎯 演示模板")
    st.caption("适合现场快速展示。可以直接载入编辑器，也可以一键保存为故障链。")

    for template in DEMO_CHAIN_TEMPLATES:
        with st.container():
            st.markdown(f"**{template['name']}**")
            st.caption(template["description"])
            col1, col2 = st.columns(2)
            with col1:
                if st.button(
                    "载入模板",
                    key=f"load_template_{template['key']}",
                    use_container_width=True,
                ):
                    load_template_into_editor(template["key"])
                    st.success(f"已载入模板：{template['name']}")
                    st.rerun()
            with col2:
                if st.button(
                    "保存到故障链列表",
                    key=f"save_template_{template['key']}",
                    use_container_width=True,
                ):
                    ok, message = save_template_to_db(template["key"])
                    if ok:
                        st.success(f"已保存模板：{template['name']}")
                        st.rerun()
                    else:
                        st.warning(message)


def load_template_into_editor(template_key: str) -> None:
    """将模板加载到当前编辑器。"""
    template = get_template(template_key)
    if not template:
        return

    st.session_state.current_stages = copy.deepcopy(template["stages"])
    st.session_state.chain_name = template["name"]
    st.session_state.chain_desc = template["description"]


def save_template_to_db(template_key: str) -> tuple[bool, str]:
    """将模板保存为可执行故障链。"""
    template = get_template(template_key)
    if not template:
        return False, "模板不存在"

    invalid_stage = next(
        (
            stage
            for stage in template["stages"]
            if stage.get("type") == "fault"
            and stage.get("pod_selector", "").strip() == "请替换为目标Pod"
        ),
        None,
    )
    if invalid_stage:
        return (
            False,
            "当前未配置演示 Pod，无法直接保存模板。请先设置 EDAP_DEMO_POD，或先载入模板后手动修改 Pod。",
        )

    db.save_drill_chain(
        template["name"],
        template["description"],
        copy.deepcopy(template["stages"]),
    )
    return True, "ok"


def get_template(template_key: str) -> dict | None:
    """按 key 获取模板。"""
    for template in DEMO_CHAIN_TEMPLATES:
        if template["key"] == template_key:
            return template
    return None
