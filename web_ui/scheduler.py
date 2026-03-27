"""
调度器模块
管理 APScheduler 定时演练调度
"""

import threading
import json as _json
from datetime import datetime
import uuid

try:
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.cron import CronTrigger
    _SCHEDULER_AVAILABLE = True
except ImportError:
    _SCHEDULER_AVAILABLE = False
    BackgroundScheduler = None
    CronTrigger = None

# 调度器实例
_scheduler = None
if _SCHEDULER_AVAILABLE:
    _scheduler = BackgroundScheduler(daemon=True)
    _scheduler.start()


def get_scheduler():
    """获取调度器实例"""
    return _scheduler


def is_scheduler_available() -> bool:
    """检查调度器是否可用"""
    return _SCHEDULER_AVAILABLE


def init_scheduler():
    """初始化调度器（如果尚未初始化）"""
    global _scheduler
    if _scheduler is None and _SCHEDULER_AVAILABLE:
        _scheduler = BackgroundScheduler(daemon=True)
        _scheduler.start()
    return _scheduler


def reload_schedules_from_db(db_module):
    """从数据库加载所有启用的演练计划，注册到 APScheduler
    
    Args:
        db_module: 数据库模块 (import db as db_module)
    """
    if not _scheduler:
        return
    
    # 移除所有旧的定时任务
    for job in _scheduler.get_jobs():
        if job.id.startswith('sched_'):
            job.remove()
    
    schedules = db_module.list_drill_schedules()
    for s in schedules:
        if not s.get('enabled', 1):
            continue
        try:
            trigger = CronTrigger.from_crontab(s['cron_expr'])
            _scheduler.add_job(
                run_scheduled_drill,
                trigger=trigger,
                id=f'sched_{s["name"]}',
                args=[s['name'], s],
                replace_existing=True,
            )
        except Exception:
            pass
    
    # 更新下次执行时间
    for job in _scheduler.get_jobs():
        if job.id.startswith('sched_'):
            name = job.id[len('sched_'):]
            next_ts = job.next_run_time
            next_str = next_ts.strftime('%Y-%m-%d %H:%M:%S') if next_ts else None
            db_module.update_schedule_run_time(name, next_str)


def run_scheduled_drill(schedule_name: str, schedule_cfg: dict, drill_executor_module, state_module, config_module):
    """APScheduler 回调：执行定时演练（无 st.* 调用）
    
    Args:
        schedule_name: 计划名称
        schedule_cfg: 计划配置
        drill_executor_module: 演练执行模块
        state_module: 状态管理模块
        config_module: 配置模块
    """
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
    
    import db as _db
    from chaos_injector import ChaosInjector
    
    scenario_type = schedule_cfg.get('scenario', 'cpu_stress')
    namespace = schedule_cfg.get('namespace', 'default')
    pod_selector = schedule_cfg.get('pod_selector', '')
    params_extra = _json.loads(schedule_cfg.get('params_json', '{}'))
    duration = params_extra.get('duration', 60)
    duration_str = f'{duration}s'
    
    try:
        k8s_profile = _db.get_default_k8s_profile()
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
        
        state_module.set_drill_task(task_id, {
            'status': 'running',
            'elapsed': 0,
            'total': duration,
            'scenario_name': f'[定时] {schedule_name}',
        })
        
        scenario_map = config_module.SCENARIO_MAP
        scenario = scenario_map.get(scenario_type, {'type': scenario_type, 'name': scenario_type})
        
        params = {
            'namespace': namespace,
            'pod_name': pod_selector,
            'scenario': scenario,
            'timeout': duration,
            'duration_str': duration_str,
            'check_interval': 5,
            **params_extra,
        }
        
        now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        _db.update_schedule_run_time(schedule_name, None, last_run=now_str)
        
        drill_executor_module.run_drill_background(params, task_id, injector, {})
    except Exception:
        pass
    finally:
        # 更新下次执行时间
        try:
            if _scheduler:
                job = _scheduler.get_job(f'sched_{schedule_name}')
                if job:
                    next_ts = job.next_run_time
                    next_str = next_ts.strftime('%Y-%m-%d %H:%M:%S') if next_ts else None
                    _db.update_schedule_run_time(schedule_name, next_str)
        except Exception:
            pass
