"""
故障链演练页面模块
"""

import streamlit as st
import sys
import os
import json
import uuid
import threading
import time
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

import db
from ..config import SCENARIO_MAP
from ..state import (
    init_session_state, get_chaos_injector, 
    get_drill_tasks, get_drill_tasks_lock
)
from ..chain_executor import ChainExecutor


def render():
    """渲染故障链演练页面"""
    init_session_state()
    st.title("🔗 多步骤故障链")

    st.info("💡 故障链功能：按顺序执行多个故障注入步骤，模拟复杂的故障场景")

    # 获取演练任务状态
    drill_tasks = get_drill_tasks()
    drill_tasks_lock = get_drill_tasks_lock()

    # 检查是否有正在执行的故障链
    if st.session_state.get('chain_in_progress'):
        _handle_running_chain(drill_tasks, drill_tasks_lock)
        return

    # 检查注入器是否就绪
    injector = get_chaos_injector()
    if injector is None:
        st.warning("⚠ 集群未连接，请先在左侧导航「⚙️ 设置」页面配置并连接集群")
        return

    # 初始化 session state 中的 stages 列表
    if 'current_stages' not in st.session_state:
        st.session_state.current_stages = []

    # 左右分栏
    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("📋 已保存的故障链")
        chains = db.list_drill_chains()

        if chains:
            for chain in chains:
                with st.expander(f"🔗 {chain['name']}", expanded=False):
                    st.caption(chain.get('description', '无描述'))
                    stages = json.loads(chain.get('stages_json', '[]'))
                    
                    # 显示步骤列表
                    for idx, stage in enumerate(stages):
                        stype = stage.get('type', 'unknown')
                        if stype == 'fault':
                            st.write(f"  {idx+1}. ⚡ 故障注入: {stage.get('scenario', 'unknown')}")
                        elif stype == 'wait':
                            st.write(f"  {idx+1}. ⏳ 等待: {stage.get('wait_seconds', 0)}秒")
                        elif stype == 'verify_alert':
                            st.write(f"  {idx+1}. 🔔 验证告警: {stage.get('alert_name', 'unknown')}")

                    # 操作按钮
                    btn_col1, btn_col2 = st.columns(2)
                    with btn_col1:
                        if st.button(f"▶️ 执行", key=f"run_{chain['id']}", use_container_width=True):
                            _start_chain_execution(chain, injector, drill_tasks, drill_tasks_lock)
                    with btn_col2:
                        if st.button(f"🗑️ 删除", key=f"del_{chain['id']}", use_container_width=True):
                            db.delete_drill_chain(chain['id'])
                            st.rerun()
        else:
            st.info("暂无保存的故障链")

    with col2:
        st.subheader("➕ 创建新故障链")

        chain_name = st.text_input("故障链名称", placeholder="例如：CPU+网络组合故障", key="chain_name")
        chain_desc = st.text_area("描述", placeholder="描述这个故障链的目的...", key="chain_desc", height=80)

        # 显示当前已添加的步骤
        if st.session_state.current_stages:
            st.write("**当前步骤列表：**")
            for idx, stage in enumerate(st.session_state.current_stages):
                stype = stage.get('type', 'unknown')
                if stype == 'fault':
                    st.write(f"  {idx+1}. ⚡ 故障注入: {stage.get('scenario', 'unknown')} ({stage.get('duration', 60)}秒)")
                elif stype == 'wait':
                    st.write(f"  {idx+1}. ⏳ 等待: {stage.get('wait_seconds', 10)}秒")
                elif stype == 'verify_alert':
                    st.write(f"  {idx+1}. 🔔 验证告警: {stage.get('alert_name', '')} 期望={stage.get('expected', 'firing')}")
            
            # 上移/下移/删除按钮
            st.write("**步骤操作：**")
            for idx, stage in enumerate(st.session_state.current_stages):
                c1, c2, c3, c4 = st.columns([3, 1, 1, 1])
                stype = stage.get('type', 'unknown')
                label = f"{idx+1}. {stype}"
                c1.write(label)
                with c2:
                    if st.button("⬆️", key=f"up_{idx}", disabled=(idx == 0)):
                        st.session_state.current_stages[idx], st.session_state.current_stages[idx-1] = \
                            st.session_state.current_stages[idx-1], st.session_state.current_stages[idx]
                        st.rerun()
                with c3:
                    if st.button("⬇️", key=f"down_{idx}", disabled=(idx == len(st.session_state.current_stages)-1)):
                        st.session_state.current_stages[idx], st.session_state.current_stages[idx+1] = \
                            st.session_state.current_stages[idx+1], st.session_state.current_stages[idx]
                        st.rerun()
                with c4:
                    if st.button("🗑️", key=f"rm_{idx}"):
                        st.session_state.current_stages.pop(idx)
                        st.rerun()

        st.markdown("---")
        st.write("**添加新步骤：**")
        
        stage_type = st.selectbox("步骤类型", ["故障注入", "等待", "验证告警"], key="new_stage_type")

        if stage_type == "故障注入":
            scenario = st.selectbox("故障场景", list(SCENARIO_MAP.keys()), key="fault_scenario")
            namespace = st.text_input("命名空间", value="default", key="fault_ns")
            pod_selector = st.text_input("Pod 名称", placeholder="目标 Pod 名称", key="fault_pod")
            duration = st.number_input("持续时间(秒)", min_value=10, value=60, key="fault_duration")
            
            # 根据场景类型显示额外参数
            extra_params = {}
            if scenario == 'cpu_stress':
                extra_params['cpu_workers'] = st.number_input("CPU Workers", min_value=1, value=1, key="cpu_workers")
                extra_params['cpu_load'] = st.number_input("CPU 负载(%)", min_value=1, max_value=100, value=100, key="cpu_load")
            elif scenario == 'memory_stress':
                extra_params['memory_size'] = st.text_input("内存大小", value="256Mi", key="mem_size")
                extra_params['memory_workers'] = st.number_input("Memory Workers", min_value=1, value=1, key="mem_workers")
            elif scenario == 'network_delay':
                extra_params['latency'] = st.text_input("延迟", value="100ms", key="net_latency")
                extra_params['jitter'] = st.text_input("抖动", value="10ms", key="net_jitter")
            elif scenario == 'disk_io':
                extra_params['path'] = st.text_input("磁盘路径", value="/var/log", key="disk_path")
                extra_params['size'] = st.text_input("填充大小", value="1Gi", key="disk_size")

            if st.button("➕ 添加故障注入步骤", use_container_width=True):
                if not pod_selector:
                    st.warning("请输入 Pod 名称")
                else:
                    new_stage = {
                        'type': 'fault',
                        'scenario': scenario,
                        'namespace': namespace,
                        'pod_selector': pod_selector,
                        'duration': duration,
                        **extra_params
                    }
                    st.session_state.current_stages.append(new_stage)
                    st.rerun()

        elif stage_type == "等待":
            wait_seconds = st.number_input("等待时间(秒)", min_value=1, value=30, key="wait_sec")
            if st.button("➕ 添加等待步骤", use_container_width=True):
                new_stage = {
                    'type': 'wait',
                    'wait_seconds': wait_seconds
                }
                st.session_state.current_stages.append(new_stage)
                st.rerun()

        else:  # 验证告警
            alert_name = st.text_input("告警名称", placeholder="例如: PodCrashLoopingOff", key="alert_name")
            expected = st.selectbox("期望状态", ["firing", "resolved"], key="alert_expected")
            if st.button("➕ 添加验证告警步骤", use_container_width=True):
                if not alert_name:
                    st.warning("请输入告警名称")
                else:
                    new_stage = {
                        'type': 'verify_alert',
                        'alert_name': alert_name,
                        'expected': expected
                    }
                    st.session_state.current_stages.append(new_stage)
                    st.rerun()

        st.markdown("---")

        # 保存和清空按钮
        c1, c2 = st.columns(2)
        with c1:
            if st.button("💾 保存故障链", type="primary", use_container_width=True):
                if not chain_name:
                    st.warning("请输入故障链名称")
                elif not st.session_state.current_stages:
                    st.warning("请至少添加一个步骤")
                else:
                    db.save_drill_chain(chain_name, chain_desc, st.session_state.current_stages)
                    st.session_state.current_stages = []
                    st.success(f"故障链「{chain_name}」已保存")
                    st.rerun()
        
        with c2:
            if st.button("🗑️ 清空当前步骤", use_container_width=True):
                st.session_state.current_stages = []
                st.rerun()


def _start_chain_execution(chain, injector, drill_tasks, drill_tasks_lock):
    """启动故障链执行"""
    task_id = str(uuid.uuid4())[:8]
    chain_name = chain['name']
    stages = json.loads(chain.get('stages_json', '[]'))
    
    if not stages:
        st.error("故障链没有步骤")
        return
    
    # 初始化任务状态
    with drill_tasks_lock:
        drill_tasks[task_id] = {
            'status': 'running',
            'chain_name': chain_name,
            'current_stage': 0,
            'total_stages': len(stages),
            'log': [],
            'start_time': datetime.now().isoformat(),
            'stop_signal': False
        }
    
    # 设置 session state
    st.session_state['chain_in_progress'] = True
    st.session_state['chain_task_id'] = task_id
    
    # 创建执行器并启动后台线程
    executor = ChainExecutor(drill_tasks, drill_tasks_lock)
    
    def run_in_thread():
        executor.run_chain(task_id, chain_name, stages, injector)
    
    thread = threading.Thread(target=run_in_thread, daemon=True)
    thread.start()
    
    st.rerun()


def _handle_running_chain(drill_tasks, drill_tasks_lock):
    """处理正在执行的故障链"""
    task_id = st.session_state.get('chain_task_id')
    if not task_id:
        st.session_state['chain_in_progress'] = False
        st.rerun()
        return
    
    # 获取任务状态
    with drill_tasks_lock:
        task = drill_tasks.get(task_id, {})
    
    if not task:
        st.session_state['chain_in_progress'] = False
        st.rerun()
        return
    
    status = task.get('status', 'unknown')
    chain_name = task.get('chain_name', '未知故障链')
    current_stage = task.get('current_stage', 0)
    total_stages = task.get('total_stages', 0)
    logs = task.get('log', [])
    
    # 显示状态
    st.subheader(f"🔗 正在执行: {chain_name}")
    
    # 进度条
    if total_stages > 0:
        progress = current_stage / total_stages
        st.progress(progress, text=f"Stage {current_stage}/{total_stages}")
    
    # 状态指示
    if status == 'running':
        st.info(f"🔄 执行中... (Stage {current_stage}/{total_stages})")
    elif status == 'done':
        st.success("✅ 执行完成!")
    elif status == 'stopped':
        st.warning("⛔ 已停止")
    elif status == 'error':
        st.error(f"❌ 执行出错: {task.get('error_msg', '未知错误')}")
    
    # 显示日志
    st.subheader("📋 执行日志")
    log_container = st.container(height=300)
    with log_container:
        for log_entry in logs:
            st.code(log_entry, language=None)
    
    # 操作按钮
    c1, c2 = st.columns(2)
    with c1:
        if status == 'running':
            if st.button("⛔ 紧急停止", type="primary", use_container_width=True):
                with drill_tasks_lock:
                    drill_tasks[task_id]['stop_signal'] = True
                st.warning("已发送停止信号...")
                time.sleep(1)
                st.rerun()
    
    with c2:
        if status in ('done', 'stopped', 'error'):
            if st.button("🔄 返回", use_container_width=True):
                st.session_state['chain_in_progress'] = False
                st.session_state['chain_task_id'] = None
                # 清理任务
                with drill_tasks_lock:
                    drill_tasks.pop(task_id, None)
                st.rerun()
    
    # 自动刷新（执行中）
    if status == 'running':
        time.sleep(2)
        st.rerun()
