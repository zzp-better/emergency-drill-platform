"""
故障注入页面模块
"""

import streamlit as st
import sys
import os
import time
import uuid
import threading
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

import db
from ..config import SCENARIO_MAP, CHAOS_MESH_SCENARIOS
from ..state import (
    init_session_state, get_chaos_injector, get_monitor_checker,
    get_drill_tasks, get_drill_tasks_lock
)
from ..utils import load_scenarios, validate_input, run_health_check, display_health_check
from ..drill_executor import run_drill_background


# Chaos Mesh 场景类型
_CHAOS_MESH_SCENARIOS = {'cpu_stress', 'network_delay', 'disk_io', 'memory_stress'}


def render():
    """渲染故障注入页面"""
    init_session_state()
    
    st.title("⚡ 故障注入")

    # 获取演练任务状态
    drill_tasks = get_drill_tasks()
    drill_tasks_lock = get_drill_tasks_lock()

    # 后台演练进行中：轮询并展示状态
    if st.session_state.get('drill_in_progress'):
        _handle_running_task(drill_tasks, drill_tasks_lock)
        return

    # 检查注入器是否就绪
    injector = get_chaos_injector()
    if injector is None:
        st.warning("⚠ 集群未连接，请先在左侧导航「⚙️ 设置」页面配置并连接集群")
        return

    # 实时监控告警状态
    _display_alert_status()

    # Chaos Mesh 开关
    use_chaos_mesh = _handle_chaos_mesh_toggle(injector)

    # 加载场景配置
    scenarios = load_scenarios()
    if not scenarios:
        st.warning("未找到故障场景配置文件，请检查 scenarios/ 目录")
        return

    # 场景选择
    st.subheader("选择故障场景")
    scenario_options = {f"{s['name']} - {s['description']}": s for s in scenarios}
    selected = st.selectbox("选择场景", list(scenario_options.keys()))
    scenario = scenario_options[selected]

    # 检查 Chaos Mesh 要求
    if scenario['type'] in _CHAOS_MESH_SCENARIOS and not use_chaos_mesh:
        st.warning(f"⚠ 「{scenario['name']}」需要 Chaos Mesh，请勾选上方「使用 Chaos Mesh」后再执行")

    st.markdown("---")
    
    # 参数配置
    st.subheader("🔧 参数配置")
    params = _collect_drill_params(scenario, injector)

    # 处理健康预检结果
    if st.session_state.get('fi_health_check_results'):
        _handle_health_check_results(drill_tasks, drill_tasks_lock)
        return

    # 执行演练
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🚀 开始演练", use_container_width=True, type="primary"):
            _start_drill(params, drill_tasks, drill_tasks_lock)


def _handle_running_task(drill_tasks, drill_tasks_lock):
    """处理正在运行的任务"""
    task_id = st.session_state.get('drill_task_id')
    with drill_tasks_lock:
        task = dict(drill_tasks.get(task_id, {}))

    if not task:
        st.session_state.drill_in_progress = False
        st.session_state.drill_task_id = None
        return

    if task['status'] == 'running':
        elapsed = task.get('elapsed', 0)
        total = task.get('total', 60)
        scenario_name = task.get('scenario_name', '')
        st.info(f"⏳ 演练进行中：{scenario_name}  ({elapsed}/{total} 秒)")
        if total > 0:
            st.progress(min(elapsed / total, 1.0))
        st.caption("演练在后台运行，可安全切换到其他页面，完成后返回此页查看结果。")
        time.sleep(2)
        st.rerun()

    elif task['status'] == 'done':
        st.session_state.drill_in_progress = False
        st.session_state.drill_task_id = None
        entry = task.get('entry', {})
        if entry:
            st.session_state.drill_history.append(entry)
        result = task.get('result', {})
        st.markdown("---")
        st.subheader("📊 演练结果")
        result_data = {
            '场景名称': entry.get('scenario', ''),
            '故障类型': entry.get('scenario_type', ''),
            '命名空间': entry.get('namespace', ''),
            'Pod 名称': entry.get('pod_name', ''),
            '演练状态': '✅ 成功' if result.get('success') else '❌ 失败',
            '耗时': f"{entry.get('duration', 0):.2f} 秒",
            '完成时间': task.get('end_time_str', ''),
        }
        for key, value in result_data.items():
            st.markdown(f"**{key}**: {value}")
        if result.get('recovery_time'):
            st.info(f"📈 Pod 恢复时间: {result['recovery_time']} 秒")
        if result.get('message'):
            st.info(f"💬 消息: {result['message']}")
        with drill_tasks_lock:
            if task_id in drill_tasks:
                drill_tasks.pop(task_id)
        st.markdown("---")

    elif task['status'] == 'error':
        st.session_state.drill_in_progress = False
        st.session_state.drill_task_id = None
        st.error(f"❌ 演练执行出错: {task.get('error_msg', '未知错误')}")
        if task.get('traceback'):
            with st.expander("详细错误"):
                st.code(task['traceback'])
        with drill_tasks_lock:
            if task_id in drill_tasks:
                drill_tasks.pop(task_id)


def _display_alert_status():
    """显示实时监控告警状态"""
    st.subheader("📊 实时监控告警状态")
    
    monitor_checker = get_monitor_checker()
    if monitor_checker is None:
        st.warning("⚠ 监控未连接，请先在设置页面配置 Prometheus")
    else:
        try:
            alerts = monitor_checker.prometheus.query_alerts()
            col_alert1, col_alert2 = st.columns(2)
            
            with col_alert1:
                firing_count = len([a for a in alerts if a.get('state') == 'firing'])
                st.metric("触发告警", firing_count)
            
            with col_alert2:
                pending_count = len([a for a in alerts if a.get('state') == 'pending'])
                st.metric("待处理告警", pending_count)
            
            if alerts:
                with st.expander("📋 活跃告警列表", expanded=len(alerts) > 5):
                    for alert in alerts[:10]:
                        alert_name = alert.get('labels', {}).get('alertname', 'N/A')
                        severity = alert.get('labels', {}).get('severity', 'N/A')
                        state = alert.get('state', 'N/A')
                        st.write(f"**{alert_name}** | 严重性: {severity} | 状态: {state}")
            else:
                st.info("暂无活跃告警")
        except Exception as e:
            st.error(f"获取告警失败: {e}")
    
    st.markdown("---")


def _handle_chaos_mesh_toggle(injector):
    """处理 Chaos Mesh 开关"""
    current_cm = getattr(injector, 'use_chaos_mesh', False)
    use_chaos_mesh = st.checkbox(
        "使用 Chaos Mesh",
        value=current_cm,
        help="CPU 压测、网络延迟、磁盘故障场景需要 Chaos Mesh；Pod 崩溃场景不需要",
    )
    
    if use_chaos_mesh != current_cm:
        from ..utils import init_chaos_injector
        st.session_state.chaos_injector = None
        init_chaos_injector(use_chaos_mesh=use_chaos_mesh, silent=True)
    
    return use_chaos_mesh


def _collect_drill_params(scenario, injector):
    """收集演练参数"""
    col1, col2 = st.columns(2)

    with col1:
        ns_col, ns_btn_col = st.columns([3, 1])
        with ns_col:
            namespace = st.text_input("命名空间", value="default")
        with ns_btn_col:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("📋 加载", help="从集群加载该命名空间的 Pod 列表", use_container_width=True):
                pods = injector.list_pods(namespace)
                st.session_state.fi_pod_list = [p['name'] for p in pods]
                st.session_state.fi_pod_ns = namespace
                st.rerun()

        pod_list = st.session_state.get('fi_pod_list', [])
        pod_ns = st.session_state.get('fi_pod_ns', '')
        if pod_list and pod_ns == namespace:
            pod_name = st.selectbox(f"选择 Pod（{len(pod_list)} 个）", pod_list)
        else:
            pod_name = st.text_input("Pod 名称", placeholder="例如: nginx-deployment-xxx")
    
    with col2:
        timeout = st.number_input("超时时间(秒)", min_value=10, max_value=600, value=60)
        check_interval = st.number_input("检查间隔(秒)", min_value=1, max_value=30, value=5)
    
    # 场景特定参数
    params = {
        'namespace': namespace,
        'pod_name': pod_name,
        'scenario': scenario,
        'timeout': timeout,
        'duration_str': f'{timeout}s',
        'check_interval': check_interval,
    }

    if scenario['type'] == 'cpu_stress':
        st.markdown("#### ⚡ CPU 压测参数")
        col_s1, col_s2 = st.columns(2)
        with col_s1:
            params['cpu_workers'] = st.number_input("CPU Workers", min_value=1, max_value=16, value=2)
        with col_s2:
            params['cpu_load'] = st.number_input("CPU 负载 (%)", min_value=1, max_value=100, value=100)

    elif scenario['type'] == 'memory_stress':
        st.markdown("#### 🧠 内存压测参数")
        col_s1, col_s2 = st.columns(2)
        with col_s1:
            params['memory_size'] = st.text_input("内存大小", value="256Mi")
        with col_s2:
            params['memory_workers'] = st.number_input("Memory Workers", min_value=1, max_value=8, value=1)

    elif scenario['type'] == 'network_delay':
        st.markdown("#### 🌐 网络延迟参数")
        col_s1, col_s2 = st.columns(2)
        with col_s1:
            params['net_latency'] = st.text_input("延迟时间", value="100ms")
        with col_s2:
            params['net_jitter'] = st.text_input("抖动", value="10ms")

    elif scenario['type'] == 'disk_io':
        st.markdown("#### 💾 磁盘故障参数")
        col_s1, col_s2 = st.columns(2)
        with col_s1:
            params['disk_path'] = st.text_input("磁盘路径", value="/var/log")
        with col_s2:
            params['disk_fault_type'] = st.selectbox("故障类型", ["disk_fill", "disk_io"])
        params['disk_size'] = st.text_input("磁盘大小", value="1Gi")

    return params


def _handle_health_check_results(drill_tasks, drill_tasks_lock):
    """处理健康预检结果"""
    check_results = st.session_state.fi_health_check_results
    has_fail = display_health_check(check_results)
    
    col_c1, col_c2 = st.columns(2)
    with col_c1:
        if st.button("▶️ 确认执行演练", use_container_width=True, type="primary"):
            params = st.session_state.fi_pending_drill_params
            st.session_state.fi_health_check_results = None
            st.session_state.fi_pending_drill_params = None
            if params:
                _start_drill_thread(params, drill_tasks, drill_tasks_lock)
                st.rerun()
    with col_c2:
        if st.button("✕ 取消", use_container_width=True):
            st.session_state.fi_health_check_results = None
            st.session_state.fi_pending_drill_params = None
            st.rerun()


def _start_drill(params, drill_tasks, drill_tasks_lock):
    """开始演练"""
    pod_name = params.get('pod_name', '')
    namespace = params.get('namespace', 'default')
    scenario = params.get('scenario', {})
    
    # 验证输入
    if not pod_name or not pod_name.strip():
        st.error("❌ Pod 名称不能为空")
        return

    is_valid, error_msg = validate_input(namespace, "命名空间")
    if not is_valid:
        st.error(f"❌ {error_msg}")
        return

    is_valid, error_msg = validate_input(pod_name, "Pod 名称")
    if not is_valid:
        st.error(f"❌ {error_msg}")
        return

    # 执行健康预检
    with st.spinner("正在执行健康预检..."):
        check_results = run_health_check(namespace, pod_name.strip(), scenario['type'])
    st.session_state.fi_health_check_results = check_results
    st.session_state.fi_pending_drill_params = params
    st.session_state.fi_force_drill = False
    st.rerun()


def _start_drill_thread(params: dict, drill_tasks: dict, drill_tasks_lock):
    """启动后台演练线程"""
    from ..utils import send_notification, generate_drill_report
    
    task_id = uuid.uuid4().hex[:8]
    injector = st.session_state.chaos_injector
    notify_cfg = dict(st.session_state.get('notify_config', {}))

    with drill_tasks_lock:
        drill_tasks[task_id] = {
            'status': 'running',
            'elapsed': 0,
            'total': params.get('timeout', 60),
            'scenario_name': params['scenario'].get('name', task_id),
        }

    st.session_state.drill_in_progress = True
    st.session_state.drill_task_id = task_id

    # 启动后台线程
    thread = threading.Thread(
        target=run_drill_background,
        args=(params, task_id, injector, notify_cfg, drill_tasks, drill_tasks_lock,
              send_notification, generate_drill_report),
        daemon=True
    )
    thread.start()
