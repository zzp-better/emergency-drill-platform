"""
演练调度器模块
负责定时演练任务的管理和执行
"""
import json
import uuid
from datetime import datetime

try:
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.cron import CronTrigger
    SCHEDULER_AVAILABLE = True
except ImportError:
    SCHEDULER_AVAILABLE = False

import db
from chaos_injector import ChaosInjector


class DrillScheduler:
    """演练调度器"""

    def __init__(self, drill_tasks, drill_tasks_lock, run_drill_func):
        self.scheduler = None
        self.drill_tasks = drill_tasks
        self.drill_tasks_lock = drill_tasks_lock
        self.run_drill_func = run_drill_func

        if SCHEDULER_AVAILABLE:
            self.scheduler = BackgroundScheduler(daemon=True)
            self.scheduler.start()
            self.reload_schedules()

    def _run_scheduled_drill(self, schedule_name: str, schedule_cfg: dict):
        """执行定时演练"""
        scenario_type = schedule_cfg.get('scenario', 'cpu_stress')
        namespace = schedule_cfg.get('namespace', 'default')
        pod_selector = schedule_cfg.get('pod_selector', '')
        params_extra = json.loads(schedule_cfg.get('params_json', '{}'))
        duration = params_extra.get('duration', 60)

        try:
            k8s_profile = db.get_default_k8s_profile()
            if not k8s_profile:
                return

            cfg = {
                'connection_type': k8s_profile.get('connection_type', 'kubeconfig'),
                'kubeconfig_path': k8s_profile.get('kubeconfig_path', ''),
                'api_server': k8s_profile.get('api_server', ''),
                'token': k8s_profile.get('token', ''),
                'ca_cert': k8s_profile.get('ca_cert', ''),
            }
            injector = ChaosInjector(config=cfg)
            task_id = uuid.uuid4().hex[:8]

            with self.drill_tasks_lock:
                self.drill_tasks[task_id] = {
                    'status': 'running',
                    'elapsed': 0,
                    'total': duration,
                    'scenario_name': f'[定时] {schedule_name}',
                }

            scenario_map = {
                'cpu_stress': {'type': 'cpu_stress', 'name': 'CPU 压力测试'},
                'memory_stress': {'type': 'memory_stress', 'name': '内存压力测试'},
                'network_delay': {'type': 'network_delay', 'name': '网络延迟'},
                'disk_io': {'type': 'disk_io', 'name': '磁盘 IO'},
                'pod_crash': {'type': 'pod_crash', 'name': 'Pod 崩溃'},
            }
            scenario = scenario_map.get(scenario_type, {'type': scenario_type, 'name': scenario_type})

            params = {
                'namespace': namespace,
                'pod_name': pod_selector,
                'scenario': scenario,
                'timeout': duration,
                'duration_str': f'{duration}s',
                'check_interval': 5,
                **params_extra,
            }

            now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            db.update_schedule_run_time(schedule_name, None, last_run=now_str)
            self.run_drill_func(params, task_id, injector, {})
        except Exception:
            pass
        finally:
            self._update_next_run(schedule_name)

    def _update_next_run(self, schedule_name: str):
        """更新下次执行时间"""
        if not self.scheduler:
            return
        try:
            job = self.scheduler.get_job(f'sched_{schedule_name}')
            if job:
                next_ts = job.next_run_time
                next_str = next_ts.strftime('%Y-%m-%d %H:%M:%S') if next_ts else None
                db.update_schedule_run_time(schedule_name, next_str)
        except Exception:
            pass

    def reload_schedules(self):
        """从数据库重新加载所有计划"""
        if not self.scheduler:
            return

        # 移除旧任务
        for job in self.scheduler.get_jobs():
            if job.id.startswith('sched_'):
                job.remove()

        # 加载启用的计划
        schedules = db.list_drill_schedules()
        for s in schedules:
            if not s.get('enabled', 1):
                continue
            try:
                trigger = CronTrigger.from_crontab(s['cron_expr'])
                self.scheduler.add_job(
                    self._run_scheduled_drill,
                    trigger=trigger,
                    id=f'sched_{s["name"]}',
                    args=[s['name'], s],
                    replace_existing=True,
                )
            except Exception:
                pass

        # 更新 next_run
        for job in self.scheduler.get_jobs():
            if job.id.startswith('sched_'):
                name = job.id[len('sched_'):]
                self._update_next_run(name)
