"""
演练执行模块
在后台线程执行演练核心逻辑
"""

import os
import sys
import time
import threading
import uuid
import json as _json
from datetime import datetime
from typing import Dict, Optional, Any

# 添加 src 目录到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import db

# Chaos Mesh 场景类型
CHAOS_MESH_SCENARIOS = {'cpu_stress', 'network_delay', 'disk_io', 'memory_stress'}

# Chaos 类型映射
CHAOS_TYPE_MAP = {
    'cpu_stress': 'stress',
    'memory_stress': 'stress',
    'network_delay': 'network_delay',
    'disk_io': 'io',
}


def run_drill_background(params: dict, task_id: str, injector, notify_cfg: dict, 
                         drill_tasks: dict, drill_tasks_lock: threading.Lock,
                         send_notification_func=None, generate_report_func=None):
    """在后台线程执行演练核心逻辑（无任何 st.* 调用）。
    
    结果写入 drill_tasks[task_id]。
    
    Args:
        params: 演练参数
        task_id: 任务ID
        injector: 故障注入器实例
        notify_cfg: 通知配置
        drill_tasks: 演练任务字典
        drill_tasks_lock: 任务锁
        send_notification_func: 发送通知的函数
        generate_report_func: 生成报告的函数
    """
    namespace = params['namespace']
    safe_pod = params['pod_name']
    scenario = params['scenario']
    timeout = params['timeout']
    duration_str = params['duration_str']
    scenario_type = scenario['type']
    check_interval = params.get('check_interval', 5)

    start_time = datetime.now()
    try:
        result = None
        if scenario_type == 'pod_crash':
            result = injector.delete_pod(namespace, safe_pod)
        elif scenario_type == 'cpu_stress':
            result = injector.inject_cpu_stress(
                namespace=namespace,
                pod_name=safe_pod,
                cpu_workers=params.get('cpu_workers', 1),
                cpu_load=params.get('cpu_load', 100),
                duration=duration_str,
            )
        elif scenario_type == 'network_delay':
            result = injector.inject_network_delay(
                namespace=namespace,
                pod_name=safe_pod,
                latency=params.get('net_latency', '100ms'),
                jitter=params.get('net_jitter', '10ms'),
                duration=duration_str,
            )
        elif scenario_type == 'disk_io':
            result = injector.inject_disk_failure(
                namespace=namespace,
                pod_name=safe_pod,
                path=params.get('disk_path', '/var/log'),
                fault_type=params.get('disk_fault_type', 'disk_fill'),
                size=params.get('disk_size', '1Gi'),
                duration=duration_str,
            )
        elif scenario_type == 'memory_stress':
            result = injector.inject_memory_stress(
                namespace=namespace,
                pod_name=safe_pod,
                memory_size=params.get('memory_size', '256Mi'),
                memory_workers=params.get('memory_workers', 1),
                duration=duration_str,
            )
        else:
            with drill_tasks_lock:
                drill_tasks[task_id] = {'status': 'error', 'error_msg': f'未知的场景类型: {scenario_type}'}
            return

        # Chaos Mesh 场景：等待实际持续时间，并定期更新进度
        stopped = False
        if result and result.get('success') and scenario_type in CHAOS_MESH_SCENARIOS:
            elapsed = 0
            while elapsed < timeout:
                step = min(check_interval, timeout - elapsed)
                time.sleep(step)
                elapsed += step
                with drill_tasks_lock:
                    if task_id in drill_tasks:
                        drill_tasks[task_id]['elapsed'] = elapsed
                        drill_tasks[task_id]['total'] = timeout
                        if drill_tasks[task_id].get('stop_signal'):
                            stopped = True
                            break

            if stopped:
                # 清理 Chaos Mesh 资源
                chaos_type_key = CHAOS_TYPE_MAP.get(scenario_type)
                chaos_name = result.get('chaos_name', '')
                if chaos_type_key and chaos_name and hasattr(injector, 'chaos_mesh') and injector.chaos_mesh:
                    try:
                        injector.chaos_mesh.delete_chaos(namespace, chaos_name, chaos_type_key)
                    except Exception:
                        pass
                with drill_tasks_lock:
                    if task_id in drill_tasks:
                        drill_tasks[task_id].update({'status': 'stopped'})
                return

        end_time = datetime.now()
        drill_duration = (end_time - start_time).total_seconds()

        _entry = {
            'time': start_time.strftime('%Y-%m-%d %H:%M:%S'),
            'scenario': scenario['name'],
            'status': '成功' if result.get('success', False) else '失败',
            'duration': round(drill_duration, 2),
            'message': result.get('message', ''),
            'namespace': namespace,
            'pod_name': safe_pod,
            'scenario_type': scenario['type'],
        }
        db.append_drill_history(_entry)

        # 发送通知
        if send_notification_func:
            notify_event = '演练完成' if result.get('success', False) else '演练失败'
            send_notification_func(notify_event, {
                'scenario': scenario['name'],
                'namespace': namespace,
                'pod_name': safe_pod,
                'status': _entry['status'],
                'duration': _entry['duration'],
            }, notify_cfg)

        # 生成报告
        if generate_report_func:
            generate_report_func(
                scenario=scenario,
                namespace=namespace,
                pod_name=safe_pod,
                start_time=start_time,
                end_time=end_time,
                drill_duration=drill_duration,
                result=result,
            )

        with drill_tasks_lock:
            if task_id in drill_tasks:
                drill_tasks[task_id].update({
                    'status': 'done',
                    'result': result,
                    'entry': _entry,
                    'drill_duration': drill_duration,
                    'end_time_str': end_time.strftime('%Y-%m-%d %H:%M:%S'),
                })

    except Exception as exc:
        import traceback as _tb
        with drill_tasks_lock:
            drill_tasks[task_id] = {
                'status': 'error',
                'error_msg': str(exc),
                'traceback': _tb.format_exc(),
            }


def run_chain_drill_background(task_id: str, chain_name: str, stages: list, 
                                injector, notify_cfg: dict,
                                drill_tasks: dict, drill_tasks_lock: threading.Lock,
                                send_notification_func=None):
    """在后台线程顺序执行多步骤故障链（无 st.* 调用）
    
    Args:
        task_id: 任务ID
        chain_name: 故障链名称
        stages: 故障阶段列表
        injector: 故障注入器实例
        notify_cfg: 通知配置
        drill_tasks: 演练任务字典
        drill_tasks_lock: 任务锁
        send_notification_func: 发送通知的函数
    """
    import requests as _req
    
    def _log(msg: str):
        """记录日志到任务"""
        with drill_tasks_lock:
            if task_id in drill_tasks:
                if 'logs' not in drill_tasks[task_id]:
                    drill_tasks[task_id]['logs'] = []
                drill_tasks[task_id]['logs'].append(msg)

    start_time = datetime.now()
    stage_results = []
    
    try:
        with drill_tasks_lock:
            if task_id in drill_tasks:
                drill_tasks[task_id]['status'] = 'running'
                drill_tasks[task_id]['current_stage'] = 0
                drill_tasks[task_id]['total_stages'] = len(stages)

        for idx, stage in enumerate(stages):
            # 检查停止信号
            with drill_tasks_lock:
                if task_id in drill_tasks and drill_tasks[task_id].get('stop_signal'):
                    with drill_tasks_lock:
                        if task_id in drill_tasks:
                            drill_tasks[task_id]['status'] = 'stopped'
                    return

            stage_type = stage.get('type', 'fault')
            
            with drill_tasks_lock:
                if task_id in drill_tasks:
                    drill_tasks[task_id]['current_stage'] = idx + 1
                    drill_tasks[task_id]['current_stage_name'] = stage.get('name', f'Stage {idx + 1}')

            if stage_type == 'wait':
                # 等待阶段
                wait_seconds = stage.get('wait_seconds', 10)
                _log(f"⏳ 等待 {wait_seconds} 秒...")
                elapsed_w = 0
                while elapsed_w < wait_seconds:
                    sleep_time = min(2, wait_seconds - elapsed_w)
                    time.sleep(sleep_time)
                    elapsed_w += sleep_time
                    # 检查停止信号
                    with drill_tasks_lock:
                        if task_id in drill_tasks and drill_tasks[task_id].get('stop_signal'):
                            with drill_tasks_lock:
                                if task_id in drill_tasks:
                                    drill_tasks[task_id]['status'] = 'stopped'
                            return
                stage_results.append({'stage': idx + 1, 'type': 'wait', 'status': 'success'})
                _log(f"✓ 等待完成")

            elif stage_type == 'alert_check':
                # 告警检查阶段
                alert_name = stage.get('alert_name', '')
                prometheus_url = stage.get('prometheus_url', '')
                _log(f"🔍 检查告警: {alert_name}")
                
                try:
                    resp = _req.get(
                        f"{prometheus_url}/api/v1/alerts",
                        params={'active': 'true'},
                        timeout=10
                    )
                    alerts = resp.json().get('data', {}).get('alerts', [])
                    found = any(a.get('labels', {}).get('alertname') == alert_name for a in alerts)
                    stage_results.append({
                        'stage': idx + 1,
                        'type': 'alert_check',
                        'status': 'success' if found else 'warning',
                        'alert_found': found
                    })
                    _log(f"{'✓' if found else '⚠'} 告警检查: {'已触发' if found else '未触发'}")
                except Exception as e:
                    stage_results.append({
                        'stage': idx + 1,
                        'type': 'alert_check',
                        'status': 'error',
                        'error': str(e)
                    })
                    _log(f"✗ 告警检查失败: {e}")

            elif stage_type == 'fault':
                # 故障注入阶段
                scenario_type = stage.get('scenario', 'cpu_stress')
                namespace = stage.get('namespace', 'default')
                pod_name = stage.get('pod_name', '')
                duration = stage.get('duration', 60)
                duration_str = f'{duration}s'
                
                _log(f"💥 执行故障: {scenario_type} -> {pod_name}")
                
                result = None
                if scenario_type == 'pod_crash':
                    result = injector.delete_pod(namespace, pod_name)
                elif scenario_type == 'cpu_stress':
                    result = injector.inject_cpu_stress(
                        namespace=namespace,
                        pod_name=pod_name,
                        cpu_workers=stage.get('cpu_workers', 1),
                        cpu_load=stage.get('cpu_load', 100),
                        duration=duration_str,
                    )
                elif scenario_type == 'network_delay':
                    result = injector.inject_network_delay(
                        namespace=namespace,
                        pod_name=pod_name,
                        latency=stage.get('net_latency', '100ms'),
                        jitter=stage.get('net_jitter', '10ms'),
                        duration=duration_str,
                    )
                elif scenario_type == 'disk_io':
                    result = injector.inject_disk_failure(
                        namespace=namespace,
                        pod_name=pod_name,
                        path=stage.get('disk_path', '/var/log'),
                        fault_type=stage.get('disk_fault_type', 'disk_fill'),
                        size=stage.get('disk_size', '1Gi'),
                        duration=duration_str,
                    )
                elif scenario_type == 'memory_stress':
                    result = injector.inject_memory_stress(
                        namespace=namespace,
                        pod_name=pod_name,
                        memory_size=stage.get('memory_size', '256Mi'),
                        memory_workers=stage.get('memory_workers', 1),
                        duration=duration_str,
                    )
                
                # 等待故障持续时间
                if result and result.get('success') and scenario_type in CHAOS_MESH_SCENARIOS:
                    elapsed_f = 0
                    while elapsed_f < duration:
                        sleep_time = min(5, duration - elapsed_f)
                        time.sleep(sleep_time)
                        elapsed_f += sleep_time
                        with drill_tasks_lock:
                            if task_id in drill_tasks and drill_tasks[task_id].get('stop_signal'):
                                # 清理资源
                                chaos_type_key = CHAOS_TYPE_MAP.get(scenario_type)
                                chaos_name = result.get('chaos_name', '')
                                if chaos_type_key and chaos_name and hasattr(injector, 'chaos_mesh') and injector.chaos_mesh:
                                    try:
                                        injector.chaos_mesh.delete_chaos(namespace, chaos_name, chaos_type_key)
                                    except Exception:
                                        pass
                                with drill_tasks_lock:
                                    if task_id in drill_tasks:
                                        drill_tasks[task_id]['status'] = 'stopped'
                                return
                
                stage_results.append({
                    'stage': idx + 1,
                    'type': 'fault',
                    'status': 'success' if (result and result.get('success')) else 'error',
                    'result': result
                })
                _log(f"{'✓' if (result and result.get('success')) else '✗'} 故障注入完成")

        # 所有阶段完成
        end_time = datetime.now()
        total_duration = (end_time - start_time).total_seconds()
        
        with drill_tasks_lock:
            if task_id in drill_tasks:
                drill_tasks[task_id].update({
                    'status': 'done',
                    'stage_results': stage_results,
                    'total_duration': total_duration,
                    'end_time_str': end_time.strftime('%Y-%m-%d %H:%M:%S'),
                })
        
        _log(f"✓ 故障链演练完成，总耗时: {total_duration:.2f}秒")

    except Exception as exc:
        import traceback as _tb
        with drill_tasks_lock:
            if task_id in drill_tasks:
                drill_tasks[task_id].update({
                    'status': 'error',
                    'error_msg': str(exc),
                    'traceback': _tb.format_exc(),
                })
