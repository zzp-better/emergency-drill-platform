"""
演练执行模块
负责后台执行演练任务
"""
import time
import uuid
from datetime import datetime
import db


class DrillExecutor:
    """演练执行器"""

    def __init__(self, drill_tasks, drill_tasks_lock):
        self.drill_tasks = drill_tasks
        self.drill_tasks_lock = drill_tasks_lock
        self.CHAOS_MESH_SCENARIOS = {'cpu_stress', 'network_delay', 'disk_io', 'memory_stress'}
        self.CHAOS_TYPE_MAP = {
            'cpu_stress': 'stress',
            'memory_stress': 'stress',
            'network_delay': 'network_delay',
            'disk_io': 'io',
        }

    def run_drill_background(self, params: dict, task_id: str, injector, notify_cfg: dict):
        """后台执行演练"""
        namespace = params['namespace']
        safe_pod = params['pod_name']
        scenario = params['scenario']
        timeout = params['timeout']
        duration_str = params['duration_str']
        scenario_type = scenario['type']
        check_interval = params.get('check_interval', 5)

        start_time = datetime.now()
        try:
            result = self._inject_fault(injector, scenario_type, namespace, safe_pod, duration_str, params)
            if not result:
                return

            # 等待并检查停止信号
            stopped = self._wait_with_progress(task_id, scenario_type, result, timeout, check_interval,
                                               injector, namespace)
            if stopped:
                return

            end_time = datetime.now()
            drill_duration = (end_time - start_time).total_seconds()

            # 保存历史记录
            entry = self._create_history_entry(start_time, scenario, result, drill_duration,
                                               namespace, safe_pod)
            db.append_drill_history(entry)

            # 发送通知
            self._send_notification(result, scenario, namespace, safe_pod, entry, notify_cfg)

            # 生成报告
            self._generate_report(scenario, namespace, safe_pod, start_time, end_time,
                                 drill_duration, result)

            with self.drill_tasks_lock:
                self.drill_tasks[task_id].update({
                    'status': 'done',
                    'result': result,
                    'entry': entry,
                    'drill_duration': drill_duration,
                    'end_time_str': end_time.strftime('%Y-%m-%d %H:%M:%S'),
                })

        except Exception as exc:
            import traceback
            with self.drill_tasks_lock:
                self.drill_tasks[task_id] = {
                    'status': 'error',
                    'error_msg': str(exc),
                    'traceback': traceback.format_exc(),
                }

    def _inject_fault(self, injector, scenario_type, namespace, pod_name, duration_str, params):
        """注入故障"""
        if scenario_type == 'pod_crash':
            return injector.delete_pod(namespace, pod_name)
        elif scenario_type == 'cpu_stress':
            return injector.inject_cpu_stress(
                namespace=namespace, pod_name=pod_name,
                cpu_workers=params.get('cpu_workers', 1),
                cpu_load=params.get('cpu_load', 100),
                duration=duration_str)
        elif scenario_type == 'network_delay':
            return injector.inject_network_delay(
                namespace=namespace, pod_name=pod_name,
                latency=params.get('net_latency', '100ms'),
                jitter=params.get('net_jitter', '10ms'),
                duration=duration_str)
        elif scenario_type == 'disk_io':
            return injector.inject_disk_failure(
                namespace=namespace, pod_name=pod_name,
                path=params.get('disk_path', '/var/log'),
                fault_type=params.get('disk_fault_type', 'disk_fill'),
                size=params.get('disk_size', '1Gi'),
                duration=duration_str)
        elif scenario_type == 'memory_stress':
            return injector.inject_memory_stress(
                namespace=namespace, pod_name=pod_name,
                memory_size=params.get('memory_size', '256Mi'),
                memory_workers=params.get('memory_workers', 1),
                duration=duration_str)
        return None

    def _wait_with_progress(self, task_id, scenario_type, result, timeout, check_interval,
                           injector, namespace):
        """等待并更新进度，检查停止信号"""
        if not (result and result.get('success') and scenario_type in self.CHAOS_MESH_SCENARIOS):
            return False

        elapsed = 0
        while elapsed < timeout:
            step = min(check_interval, timeout - elapsed)
            time.sleep(step)
            elapsed += step

            with self.drill_tasks_lock:
                self.drill_tasks[task_id]['elapsed'] = elapsed
                self.drill_tasks[task_id]['total'] = timeout
                if self.drill_tasks[task_id].get('stop_signal'):
                    self._cleanup_chaos(injector, namespace, result, scenario_type)
                    self.drill_tasks[task_id].update({'status': 'stopped'})
                    return True
        return False

    def _cleanup_chaos(self, injector, namespace, result, scenario_type):
        """清理 Chaos Mesh 资源"""
        chaos_type_key = self.CHAOS_TYPE_MAP.get(scenario_type)
        chaos_name = result.get('chaos_name', '')
        if chaos_type_key and chaos_name and hasattr(injector, 'chaos_mesh') and injector.chaos_mesh:
            try:
                injector.chaos_mesh.delete_chaos(namespace, chaos_name, chaos_type_key)
            except Exception:
                pass

    def _create_history_entry(self, start_time, scenario, result, drill_duration, namespace, pod_name):
        """创建历史记录条目"""
        return {
            'time': start_time.strftime('%Y-%m-%d %H:%M:%S'),
            'scenario': scenario['name'],
            'status': '成功' if result.get('success', False) else '失败',
            'duration': round(drill_duration, 2),
            'message': result.get('message', ''),
            'namespace': namespace,
            'pod_name': pod_name,
            'scenario_type': scenario['type'],
        }

    def _send_notification(self, result, scenario, namespace, pod_name, entry, notify_cfg):
        """发送通知（占位）"""
        pass

    def _generate_report(self, scenario, namespace, pod_name, start_time, end_time,
                        drill_duration, result):
        """生成报告（占位）"""
        pass
