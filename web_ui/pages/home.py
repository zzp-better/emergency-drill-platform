"""
首页页面模块
"""

import streamlit as st
import pandas as pd
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

import db
from ..config import PAGE_CONFIG, NAVIGATION_MENU, SCENARIO_MAP
from ..styles import apply_styles
from ..state import init_session_state, get_drill_history, get_drill_tasks


def render():
    """渲染首页"""
    # 初始化会话状态
    init_session_state()
    
    # 应用样式
    apply_styles()
    
    # 加载演练历史
    history = get_drill_history()
    
    # 统计卡片
    total = len(history)
    success = len([d for d in history if d.get('status') == '成功'])
    rate = f"{success / total * 100:.1f}%" if total else "—"
    
    # 计算平均耗时
    avg_dur = 0
    if total:
        durs = [d.get('duration', 0) for d in history if d.get('duration', 0) > 0]
        if durs:
            avg_dur = sum(durs) / len(durs)
    
    # 页面标题
    st.markdown('<div class="main-header">应急演练智能平台</div>', unsafe_allow_html=True)
    st.markdown("### 🏠 平台概览")
    
    # 统计卡片行
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("总演练次数", total)
    with col2:
        st.metric("成功次数", success)
    with col3:
        st.metric("成功率", rate)
    with col4:
        st.metric("平均耗时", f"{avg_dur:.1f}s" if avg_dur else "—")
    
    st.markdown("---")
    
    # 快速操作区域
    st.markdown("### 🚀 快速操作")
    qa1, qa2, qa3, qa4 = st.columns(4)
    
    with qa1:
        if st.button("💥 故障注入", use_container_width=True):
            st.session_state.page = "fault_injection"
            st.rerun()
    
    with qa2:
        if st.button("🔗 故障链演练", use_container_width=True):
            st.session_state.page = "chain_drill"
            st.rerun()
    
    with qa3:
        if st.button("📊 演练报告", use_container_width=True):
            st.session_state.page = "reports"
            st.rerun()
    
    with qa4:
        if st.button("⚙️ 系统设置", use_container_width=True):
            st.session_state.page = "settings"
            st.rerun()
    
    st.markdown("---")
    
    # 演练任务状态
    st.markdown("### 📋 演练任务状态")
    drill_tasks = get_drill_tasks()
    running_tasks = {k: v for k, v in drill_tasks.items() if v.get('status') == 'running'}
    
    if running_tasks:
        for task_id, task in running_tasks.items():
            with st.container():
                col1, col2, col3 = st.columns([3, 2, 1])
                with col1:
                    st.write(f"**{task.get('scenario_name', task_id)}**")
                with col2:
                    elapsed = task.get('elapsed', 0)
                    total_time = task.get('total', 0)
                    if total_time > 0:
                        progress = min(elapsed / total_time, 1.0)
                        st.progress(progress)
                        st.caption(f"{elapsed}/{total_time} 秒")
                with col3:
                    if st.button("⏹ 停止", key=f"stop_{task_id}"):
                        from ..state import send_stop_signal
                        send_stop_signal(task_id)
                        st.rerun()
    else:
        st.info("暂无进行中的演练任务")
    
    st.markdown("---")
    
    # 即将执行的演练计划
    st.markdown("### 📅 即将执行的演练计划")
    all_schedules = db.list_drill_schedules()
    upcoming = [s for s in all_schedules if s.get('enabled', 1)]
    
    if upcoming:
        with st.expander(f"即将执行的演练计划（{len(upcoming)} 条）", expanded=bool(upcoming)):
            for s in upcoming:
                col1, col2, col3 = st.columns([2, 2, 1])
                with col1:
                    st.write(f"**{s['name']}**")
                with col2:
                    st.caption(f"Cron: `{s['cron_expr']}`")
                with col3:
                    if s.get('next_run'):
                        st.caption(f"下次执行: {s['next_run']}")
    else:
        st.info("暂无定时演练计划")
    
    st.markdown("---")
    
    # 最近演练历史
    st.markdown("### 📜 最近演练历史")
    if history:
        recent = history[-10:][::-1]  # 最近10条，倒序显示
        for item in recent:
            status_icon = "✅" if item.get('status') == '成功' else "❌"
            status_class = "status-success" if item.get('status') == '成功' else "status-error"
            st.markdown(
                f"""
                <div style="padding: 8px; margin: 4px 0; border-radius: 4px; background-color: #f8f9fa;">
                    {status_icon} <strong>{item.get('scenario', 'N/A')}</strong>
                    <span class="{status_class}">[{item.get('status', 'N/A')}]</span>
                    <br/>
                    <small>命名空间: {item.get('namespace', 'N/A')} | Pod: {item.get('pod_name', 'N/A')}</small>
                    <br/>
                    <small>时间: {item.get('time', 'N/A')} | 耗时: {item.get('duration', 0):.2f}s</small>
                </div>
                """,
                unsafe_allow_html=True
            )
    else:
        st.info("暂无演练历史记录")
