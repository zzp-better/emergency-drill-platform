"""
演练报告页面模块
"""

import streamlit as st
import pandas as pd
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

import db
from ..drill_reporting import list_report_summaries, render_latest_report_summary
from ..state import init_session_state, get_drill_history


from ..utils import format_duration


def render():
    """渲染演练报告页面"""
    init_session_state()

    st.title("📄 演练报告")

    # 报告列表
    reports_dir = "reports"
    report_summaries = list_report_summaries(reports_dir)

    history = get_drill_history()
    render_latest_report_summary(report_summaries, history)
    st.markdown("---")

    if not os.path.exists(reports_dir):
        st.info("reports/ 目录不存在，请先执行演练生成报告")
    elif report_summaries:
        st.subheader("📋 报告列表")

        for report in report_summaries:
            report_name = report["file_name"]
            metadata = report.get("metadata", {})
            title = metadata.get("scenario_name", report_name)
            subtitle = metadata.get("status", "未知状态")
            with st.expander(f"{title} | {subtitle} | {report_name}"):
                try:
                    with open(report["path"], "r", encoding="utf-8") as f:
                        content = f.read()
                        st.markdown(content)

                        col1, col2 = st.columns(2)
                        with col1:
                            st.download_button(
                                label="📥 下载报告",
                                data=content,
                                file_name=report_name,
                                mime="text/markdown",
                            )
                        with col2:
                            generated_at = metadata.get("generated_at")
                            if generated_at:
                                st.caption(f"生成时间: {generated_at}")
                except Exception as e:
                    st.error(f"读取报告失败: {e}")
    else:
        st.info("暂无演练报告，请先执行演练")

    st.markdown("---")

    # 演练统计
    st.subheader("📊 演练统计")

    if history:
        df = pd.DataFrame(history)

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("总演练次数", len(df))

        with col2:
            if "duration" in df.columns:
                avg_duration = df["duration"].mean()
                st.metric("平均耗时", f"{avg_duration:.2f} 秒")
            else:
                st.metric("平均耗时", "N/A")

        with col3:
            success_count = len(df[df["status"] == "成功"])
            success_rate = (success_count / len(df)) * 100
            st.metric("成功率", f"{success_rate:.1f}%")

        # 场景分布
        st.markdown("---")
        st.subheader("场景分布")

        if "scenario" in df.columns:
            scenario_counts = df["scenario"].value_counts()
            st.bar_chart(scenario_counts, horizontal=True)
    else:
        st.info("暂无演练数据")
