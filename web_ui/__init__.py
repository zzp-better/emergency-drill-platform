"""
Web UI 模块
应急演练智能平台的 Web 界面模块化组件
"""

from .config import (
    DEFAULT_CLUSTER,
    DEFAULT_MONITOR,
    DEFAULT_GRAFANA,
    PAGE_CONFIG,
    NAVIGATION_MENU,
    SCENARIO_MAP,
    CHAOS_MESH_SCENARIOS,
)
from .styles import CUSTOM_CSS, apply_styles
from .state import (
    _drill_tasks,
    _drill_tasks_lock,
    get_drill_task,
    set_drill_task,
    remove_drill_task,
    get_all_drill_tasks,
    get_running_tasks,
    send_stop_signal,
    check_stop_signal,
    init_session_state,
    get_chaos_injector,
    set_chaos_injector,
    get_monitor_checker,
    set_monitor_checker,
)
from .utils import (
    load_scenarios,
    validate_input,
    build_injector,
    init_chaos_injector,
    init_monitor_checker,
    format_duration,
    get_scenario_display_name,
    run_health_check,
    display_health_check,
    send_notification,
    generate_drill_report,
)

__all__ = [
    # 配置
    'DEFAULT_CLUSTER',
    'DEFAULT_MONITOR',
    'DEFAULT_GRAFANA',
    'PAGE_CONFIG',
    'NAVIGATION_MENU',
    'SCENARIO_MAP',
    'CHAOS_MESH_SCENARIOS',
    # 样式
    'CUSTOM_CSS',
    'apply_styles',
    # 状态管理
    '_drill_tasks',
    '_drill_tasks_lock',
    'get_drill_task',
    'set_drill_task',
    'remove_drill_task',
    'get_all_drill_tasks',
    'get_running_tasks',
    'send_stop_signal',
    'check_stop_signal',
    'init_session_state',
    'get_chaos_injector',
    'set_chaos_injector',
    'get_monitor_checker',
    'set_monitor_checker',
    # 工具函数
    'load_scenarios',
    'validate_input',
    'build_injector',
    'init_chaos_injector',
    'init_monitor_checker',
    'format_duration',
    'get_scenario_display_name',
    'run_health_check',
    'display_health_check',
    'send_notification',
    'generate_drill_report',
]
