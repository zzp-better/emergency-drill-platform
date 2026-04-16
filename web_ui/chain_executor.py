"""
故障链执行模块
负责多步骤故障链的后台执行
"""
import time
import json
from datetime import datetime
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import db
from chaos_injector import ChaosInjector
from .drill_executor import inject_fault, CHAOS_MESH_SCENARIOS, _cleanup_chaos_mesh


class ChainExecutor:
    """故障链执行器"""

    def __init__(self, drill_tasks, drill_tasks_lock):
        self.drill_tasks = drill_tasks
        self.drill_tasks_lock = drill_tasks_lock
        self.log_entries = []

    def _log(self, task_id: str, msg: str):
        """记录日志"""
        ts = datetime.now().strftime('%H:%M:%S')
        self.log_entries.append(f'[{ts}] {msg}')
        with self.drill_tasks_lock:
            self.drill_tasks[task_id]['log'] = list(self.log_entries)

    def _check_stop(self, task_id: str) -> bool:
        """检查是否需要停止"""
        with self.drill_tasks_lock:
            return self.drill_tasks[task_id].get('stop_signal', False)

    def execute_wait_stage(self, task_id: str, stage: dict):
        """执行等待阶段"""
        wait_sec = int(stage.get('wait_seconds', 10))
        self._log(task_id, f'  等待 {wait_sec} 秒...')

        elapsed = 0
        while elapsed < wait_sec:
            step = min(2, wait_sec - elapsed)
            time.sleep(step)
            elapsed += step
            if self._check_stop(task_id):
                self._log(task_id, '⛔ 用户中断等待阶段')
                return False

        self._log(task_id, '  ✓ 等待完成')
        return True

    def execute_verify_alert_stage(self, task_id: str, stage: dict):
        """执行告警验证阶段"""
        import requests

        alert_name = stage.get('alert_name', '')
        expected = stage.get('expected', 'firing')

        try:
            mon_profile = db.get_default_monitor_profile()
            prom_url = mon_profile.get('prometheus_url', '') if mon_profile else ''
            resp = requests.get(f'{prom_url}/api/v1/alerts', timeout=5)
            alerts_data = resp.json().get('data', {}).get('alerts', [])

            firing = any(
                a.get('labels', {}).get('alertname') == alert_name and a.get('state') == 'firing'
                for a in alerts_data
            )
            ok = (firing and expected == 'firing') or (not firing and expected == 'resolved')
            self._log(task_id, f'  告警 {alert_name}: {"触发" if firing else "未触发"} — {"✓" if ok else "✗"}')
        except Exception as e:
            self._log(task_id, f'  ✗ 查询告警失败: {e}')

        return True

    def execute_fault_stage(self, task_id: str, stage: dict, injector):
        """执行故障注入阶段（支持所有场景类型，包含自定义脚本）"""
        scenario_type = stage.get('scenario', 'cpu_stress')
        namespace = stage.get('namespace', 'default')
        pod_selector = stage.get('pod_selector', '')
        duration = int(stage.get('duration', 60))
        duration_str = f'{duration}s'

        self._log(task_id, f'  注入故障: {scenario_type}')

        try:
            result = inject_fault(injector, scenario_type, namespace, pod_selector, duration_str, stage)
            if result is None:
                self._log(task_id, f'  ✗ 未知场景类型: {scenario_type}')
                return True

            if result.get('success'):
                self._log(task_id, '  ✓ 故障注入成功')
                # custom_script 场景展示输出
                if scenario_type == 'custom_script' and result.get('stdout'):
                    for line in result['stdout'].splitlines()[:10]:
                        self._log(task_id, f'    {line}')
                # 等待 Chaos Mesh 故障持续时间
                self._wait_fault_duration(task_id, duration, result, scenario_type, injector, namespace)
            else:
                self._log(task_id, f'  ✗ 故障注入失败: {result.get("message", "未知错误")}')
        except Exception as e:
            self._log(task_id, f'  ✗ 故障注入异常: {e}')

        return True

    def _wait_fault_duration(self, task_id, duration, result, scenario_type, injector, namespace):
        """等待故障持续时间（仅 Chaos Mesh 场景需要）"""
        if scenario_type not in CHAOS_MESH_SCENARIOS:
            return True

        elapsed = 0
        while elapsed < duration:
            time.sleep(min(5, duration - elapsed))
            elapsed += 5
            if self._check_stop(task_id):
                _cleanup_chaos_mesh(injector, scenario_type, namespace, result)
                return False
        return True

    def run_chain(self, task_id: str, chain_name: str, stages: list, injector):
        """执行完整故障链"""
        self.log_entries = []
        start_time = datetime.now()

        try:
            for idx, stage in enumerate(stages):
                if self._check_stop(task_id):
                    self._log(task_id, f'⛔ 用户中断，在 Stage {idx + 1} 前停止')
                    with self.drill_tasks_lock:
                        self.drill_tasks[task_id]['status'] = 'stopped'
                    return

                with self.drill_tasks_lock:
                    self.drill_tasks[task_id]['current_stage'] = idx + 1
                    self.drill_tasks[task_id]['total_stages'] = len(stages)

                stype = stage.get('type', 'wait')
                self._log(task_id, f'▶ Stage {idx + 1}/{len(stages)}: {stype}')

                if stype == 'wait':
                    if not self.execute_wait_stage(task_id, stage):
                        with self.drill_tasks_lock:
                            self.drill_tasks[task_id]['status'] = 'stopped'
                        return
                elif stype == 'verify_alert':
                    self.execute_verify_alert_stage(task_id, stage)
                elif stype == 'fault':
                    self.execute_fault_stage(task_id, stage, injector)

            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            self._log(task_id, f'✅ 故障链执行完成，耗时 {duration:.1f} 秒')

            with self.drill_tasks_lock:
                self.drill_tasks[task_id]['status'] = 'done'
                self.drill_tasks[task_id]['drill_duration'] = duration

        except Exception as e:
            self._log(task_id, f'❌ 执行异常: {e}')
            with self.drill_tasks_lock:
                self.drill_tasks[task_id]['status'] = 'error'
                self.drill_tasks[task_id]['error_msg'] = str(e)

