"""
应急演练智能平台 - Web UI
基于 Streamlit 实现的可视化界面

功能：
1. 故障注入管理
2. 监控告警验证
3. 演练报告展示
"""

import streamlit as st
import yaml
import os
import sys
import time
import threading
import uuid
import json as _json
from datetime import datetime
import pandas as pd
try:
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.cron import CronTrigger
    _SCHEDULER_AVAILABLE = True
except ImportError:
    _SCHEDULER_AVAILABLE = False

# 添加 src 目录到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from chaos_injector import ChaosInjector
from monitor_checker import MonitorChecker
from grafana_integration import GrafanaIntegration, create_grafana_integration_from_config
import db

# 初始化数据库（建表 + 迁移旧 JSON）
db.init_db()

# ── APScheduler 定时演练调度器 ──────────────────────────────────────────────────
_scheduler = None
if _SCHEDULER_AVAILABLE:
    _scheduler = BackgroundScheduler(daemon=True)
    _scheduler.start()


def _run_scheduled_drill(schedule_name: str, schedule_cfg: dict):
    """APScheduler 回调：执行定时演练（无 st.* 调用）"""
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
        with _drill_tasks_lock:
            _drill_tasks[task_id] = {
                'status': 'running', 'elapsed': 0, 'total': duration,
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
            'duration_str': duration_str,
            'check_interval': 5,
            **params_extra,
        }
        now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        _db.update_schedule_run_time(schedule_name, None, last_run=now_str)
        _run_drill_background(params, task_id, injector, {})
    except Exception:
        pass
    finally:
        # 更新下次执行时间
        try:
            job = _scheduler.get_job(f'sched_{schedule_name}')
            if job:
                next_ts = job.next_run_time
                next_str = next_ts.strftime('%Y-%m-%d %H:%M:%S') if next_ts else None
                _db.update_schedule_run_time(schedule_name, next_str)
        except Exception:
            pass


def _reload_schedules_from_db():
    """从 DB 加载所有启用的演练计划，注册到 APScheduler"""
    if not _scheduler:
        return
    # 移除所有旧的定时任务
    for job in _scheduler.get_jobs():
        if job.id.startswith('sched_'):
            job.remove()
    schedules = db.list_drill_schedules()
    for s in schedules:
        if not s.get('enabled', 1):
            continue
        try:
            trigger = CronTrigger.from_crontab(s['cron_expr'])
            _scheduler.add_job(
                _run_scheduled_drill,
                trigger=trigger,
                id=f'sched_{s["name"]}',
                args=[s['name'], s],
                replace_existing=True,
            )
        except Exception:
            pass
    # 更新 next_run
    for job in _scheduler.get_jobs():
        if job.id.startswith('sched_'):
            name = job.id[len('sched_'):]
            next_ts = job.next_run_time
            next_str = next_ts.strftime('%Y-%m-%d %H:%M:%S') if next_ts else None
            db.update_schedule_run_time(name, next_str)


# 启动时加载已有计划
_reload_schedules_from_db()

# ── 后台演练任务存储（跨 Streamlit rerun 保持任务状态）────────────────────────────
_drill_tasks: dict = {}        # task_id → {'status': 'running'|'done'|'error', ...}
_drill_tasks_lock = threading.Lock()

# 页面配置
st.set_page_config(
    page_title="应急演练智能平台",
    page_icon="🚨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 自定义 CSS
st.markdown("""
<style>
/* ════════════════════════════════════════════════════
   全局字体与颜色变量
════════════════════════════════════════════════════ */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

:root {
    --primary:     #3B82F6;
    --primary-dark:#2563EB;
    --danger:      #EF4444;
    --danger-dark: #DC2626;
    --success:     #10B981;
    --warning:     #F59E0B;
    --sidebar-bg:  #0F172A;
    --sidebar-2:   #1E293B;
    --card-bg:     #FFFFFF;
    --page-bg:     #F1F5F9;
    --text-1:      #0F172A;
    --text-2:      #475569;
    --text-3:      #94A3B8;
    --border:      #E2E8F0;
    --radius:      12px;
    --radius-sm:   8px;
    --shadow-sm:   0 1px 3px rgba(0,0,0,.08), 0 1px 2px rgba(0,0,0,.05);
    --shadow:      0 4px 12px rgba(0,0,0,.08), 0 2px 4px rgba(0,0,0,.04);
    --shadow-lg:   0 10px 30px rgba(0,0,0,.10), 0 4px 10px rgba(0,0,0,.06);
}

html, body, [class*="css"] {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
}

/* 主内容区背景 */
.stApp {
    background: var(--page-bg);
}

/* ════════════════════════════════════════════════════
   侧边栏
════════════════════════════════════════════════════ */
section[data-testid="stSidebar"] > div {
    background: #1A2235 !important;
    border-right: 1px solid #243049;
}

/* 标题区 */
section[data-testid="stSidebar"] h1 {
    color: #FFFFFF !important;
    font-size: 1.25rem !important;
    font-weight: 800 !important;
    letter-spacing: -0.3px;
    padding: 4px 0 10px 0;
}

/* 主文字 —— 提高至近白色，确保在深色底下清晰可读 */
section[data-testid="stSidebar"] .stMarkdown p,
section[data-testid="stSidebar"] .stRadio label,
section[data-testid="stSidebar"] p {
    color: #E2E8F0 !important;
}

/* 分区小标题（如"系统状态"）*/
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3,
section[data-testid="stSidebar"] .stSubheader {
    color: #64748B !important;
    font-size: 0.65rem !important;
    font-weight: 700 !important;
    text-transform: uppercase;
    letter-spacing: .12em;
}

/* ── 导航 Radio 样式 ── */
section[data-testid="stSidebar"] .stRadio > div {
    gap: 3px !important;
}

/* 每一项默认：大号字 + 近白色文字 */
section[data-testid="stSidebar"] .stRadio label {
    background: transparent !important;
    border-radius: 8px !important;
    padding: 10px 14px !important;
    transition: background .15s, color .15s !important;
    cursor: pointer;
    width: 100%;
    color: #D1D9E6 !important;
    font-size: 0.92rem !important;
    font-weight: 500 !important;
    border-left: 3px solid transparent !important;
}

/* Hover：稍亮背景 + 纯白文字 */
section[data-testid="stSidebar"] .stRadio label:hover {
    background: #243049 !important;
    color: #FFFFFF !important;
}

/* ── 选中状态（双选择器保证兼容性）──
   方案1: :has(input:checked) — 现代浏览器
   方案2: [aria-checked="true"] — 旧版 Streamlit DOM   */
section[data-testid="stSidebar"] label[data-baseweb="radio"]:has(input:checked),
section[data-testid="stSidebar"] .stRadio [aria-checked="true"] {
    background: #3B82F6 !important;
    border-left: 3px solid #93C5FD !important;
    box-shadow: 0 2px 10px rgba(59, 130, 246, 0.4) !important;
}

/* 选中项文字强制白色 */
section[data-testid="stSidebar"] label[data-baseweb="radio"]:has(input:checked) *,
section[data-testid="stSidebar"] label[data-baseweb="radio"]:has(input:checked) {
    color: #FFFFFF !important;
}

/* 隐藏 Radio 原生圆形按钮（用背景色表示选中更清晰）*/
section[data-testid="stSidebar"] [data-baseweb="radio"] > div:first-child {
    display: none !important;
}

/* 分隔线 */
section[data-testid="stSidebar"] hr {
    border-color: #243049 !important;
    margin: 10px 0;
}

/* 侧边栏内的 Alert 组件 */
section[data-testid="stSidebar"] .stAlert {
    border-radius: 8px !important;
    font-size: 0.82rem !important;
}
section[data-testid="stSidebar"] [data-testid="stNotification"] {
    background: #243049 !important;
    border-color: #334E6E !important;
}
section[data-testid="stSidebar"] [data-testid="stNotification"] p,
section[data-testid="stSidebar"] [data-testid="stNotification"] span {
    color: #E2E8F0 !important;
}

/* ════════════════════════════════════════════════════
   页头
════════════════════════════════════════════════════ */
.main-header {
    font-size: 2.4rem;
    font-weight: 800;
    background: linear-gradient(135deg, #EF4444 0%, #3B82F6 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    text-align: center;
    padding: 0.6rem 0 0.2rem 0;
    letter-spacing: -1px;
    line-height: 1.2;
}

/* ════════════════════════════════════════════════════
   通用卡片
════════════════════════════════════════════════════ */
.edap-card {
    background: var(--card-bg);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 18px 20px;
    margin-bottom: 12px;
    box-shadow: var(--shadow-sm);
    transition: box-shadow .2s, transform .2s;
}
.edap-card:hover {
    box-shadow: var(--shadow);
    transform: translateY(-1px);
}

/* ── Metric 卡片 ── */
.metric-card {
    background: var(--card-bg);
    border-radius: var(--radius);
    padding: 20px 22px;
    box-shadow: var(--shadow);
    border-top: 4px solid transparent;
    position: relative;
    overflow: hidden;
}
.metric-card::after {
    content: '';
    position: absolute;
    top: 0; right: 0;
    width: 80px; height: 80px;
    border-radius: 50%;
    background: currentColor;
    opacity: .04;
    transform: translate(30%, -30%);
}
.metric-card.blue  { border-top-color: #3B82F6; color: #3B82F6; }
.metric-card.green { border-top-color: #10B981; color: #10B981; }
.metric-card.amber { border-top-color: #F59E0B; color: #F59E0B; }
.metric-card.red   { border-top-color: #EF4444; color: #EF4444; }

.metric-card .mc-icon {
    font-size: 1.8rem;
    margin-bottom: 8px;
    display: block;
}
.metric-card .mc-value {
    font-size: 2rem;
    font-weight: 800;
    color: var(--text-1);
    line-height: 1;
    margin-bottom: 4px;
}
.metric-card .mc-label {
    font-size: 0.78rem;
    color: var(--text-3);
    text-transform: uppercase;
    letter-spacing: .06em;
    font-weight: 600;
}
.metric-card .mc-sub {
    font-size: 0.82rem;
    color: var(--text-2);
    margin-top: 6px;
}

/* ════════════════════════════════════════════════════
   状态徽章
════════════════════════════════════════════════════ */
.badge {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    border-radius: 20px;
    padding: 3px 10px;
    font-size: 0.75rem;
    font-weight: 600;
    line-height: 1.5;
}
.badge-ok   { background: #D1FAE5; color: #065F46; }
.badge-warn { background: #FEF3C7; color: #92400E; }
.badge-err  { background: #FEE2E2; color: #991B1B; }
.badge-info { background: #DBEAFE; color: #1E40AF; }
.badge-gray { background: #F1F5F9; color: #475569; }

.status-success { color: #059669; font-weight: 600; }
.status-error   { color: #DC2626; font-weight: 600; }
.status-warning { color: #D97706; font-weight: 600; }

/* ════════════════════════════════════════════════════
   分区标题
════════════════════════════════════════════════════ */
.section-title {
    font-size: 0.72rem;
    font-weight: 700;
    color: var(--text-3);
    text-transform: uppercase;
    letter-spacing: .1em;
    padding: 0 0 8px 0;
    border-bottom: 2px solid var(--border);
    margin-bottom: 14px;
}

/* ════════════════════════════════════════════════════
   快捷操作卡片（首页）
════════════════════════════════════════════════════ */
.quick-action {
    background: var(--card-bg);
    border: 1.5px solid var(--border);
    border-radius: var(--radius);
    padding: 16px 18px;
    display: flex;
    align-items: center;
    gap: 12px;
    cursor: pointer;
    transition: border-color .2s, box-shadow .2s, transform .2s;
}
.quick-action:hover {
    border-color: var(--primary);
    box-shadow: 0 0 0 3px rgba(59,130,246,.1);
    transform: translateY(-1px);
}
.quick-action .qa-icon { font-size: 1.5rem; }
.quick-action .qa-label { font-size: 0.9rem; font-weight: 600; color: var(--text-1); }
.quick-action .qa-desc { font-size: 0.78rem; color: var(--text-2); }

/* ════════════════════════════════════════════════════
   按钮覆盖
════════════════════════════════════════════════════ */
.stButton > button {
    border-radius: var(--radius-sm) !important;
    font-weight: 600 !important;
    font-size: 0.875rem !important;
    padding: 8px 16px !important;
    transition: all .15s !important;
    border-width: 1.5px !important;
}
.stButton > button:hover {
    transform: translateY(-1px);
    box-shadow: var(--shadow-sm);
}
/* Primary button */
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%) !important;
    border-color: var(--primary-dark) !important;
    box-shadow: 0 2px 8px rgba(59,130,246,.3) !important;
}
.stButton > button[kind="primary"]:hover {
    box-shadow: 0 4px 14px rgba(59,130,246,.4) !important;
}

/* ════════════════════════════════════════════════════
   输入框 / 选择框
════════════════════════════════════════════════════ */
.stTextInput > div > div > input,
.stTextArea > div > div > textarea,
.stSelectbox > div > div {
    border-radius: var(--radius-sm) !important;
    border: 1.5px solid var(--border) !important;
    font-size: 0.875rem !important;
    transition: border-color .15s, box-shadow .15s !important;
}
.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus {
    border-color: var(--primary) !important;
    box-shadow: 0 0 0 3px rgba(59,130,246,.12) !important;
}

/* ════════════════════════════════════════════════════
   Metric 组件（Streamlit 原生）
════════════════════════════════════════════════════ */
[data-testid="metric-container"] {
    background: var(--card-bg);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 14px 18px !important;
    box-shadow: var(--shadow-sm);
}
[data-testid="stMetricLabel"] {
    font-size: 0.78rem !important;
    color: var(--text-3) !important;
    text-transform: uppercase;
    letter-spacing: .05em;
    font-weight: 600 !important;
}
[data-testid="stMetricValue"] {
    font-size: 1.8rem !important;
    font-weight: 800 !important;
    color: var(--text-1) !important;
}

/* ════════════════════════════════════════════════════
   Expander
════════════════════════════════════════════════════ */
[data-testid="stExpander"] {
    border: 1.5px solid var(--border) !important;
    border-radius: var(--radius) !important;
    box-shadow: var(--shadow-sm) !important;
    overflow: hidden;
    margin-bottom: 8px;
}
[data-testid="stExpander"] > details > summary {
    background: var(--card-bg) !important;
    padding: 12px 16px !important;
    font-weight: 600 !important;
    font-size: 0.875rem !important;
    color: var(--text-1) !important;
    transition: background .15s;
}
[data-testid="stExpander"] > details > summary:hover {
    background: #F8FAFC !important;
}
[data-testid="stExpander"] > details[open] > summary {
    border-bottom: 1.5px solid var(--border);
}

/* ════════════════════════════════════════════════════
   Tabs
════════════════════════════════════════════════════ */
.stTabs [data-baseweb="tab-list"] {
    gap: 4px;
    background: var(--card-bg);
    border-radius: var(--radius) var(--radius) 0 0;
    padding: 4px 4px 0 4px;
    border-bottom: 2px solid var(--border);
}
.stTabs [data-baseweb="tab"] {
    border-radius: var(--radius-sm) var(--radius-sm) 0 0 !important;
    padding: 8px 16px !important;
    font-size: 0.875rem !important;
    font-weight: 600 !important;
    color: var(--text-2) !important;
    transition: all .15s !important;
}
.stTabs [aria-selected="true"] {
    color: var(--primary) !important;
    background: transparent !important;
    border-bottom: 2px solid var(--primary) !important;
}

/* ════════════════════════════════════════════════════
   Dataframe / 表格
════════════════════════════════════════════════════ */
.stDataFrame {
    border-radius: var(--radius) !important;
    overflow: hidden;
    border: 1.5px solid var(--border) !important;
    box-shadow: var(--shadow-sm) !important;
}

/* ════════════════════════════════════════════════════
   Alert / info / warning / error
════════════════════════════════════════════════════ */
.stAlert {
    border-radius: var(--radius-sm) !important;
    border-width: 1.5px !important;
    font-size: 0.875rem !important;
}
[data-testid="stNotification"] {
    border-radius: var(--radius-sm) !important;
}

/* ════════════════════════════════════════════════════
   Progress bar
════════════════════════════════════════════════════ */
.stProgress > div > div > div > div {
    background: linear-gradient(90deg, var(--primary) 0%, #60A5FA 100%) !important;
    border-radius: 4px !important;
}

/* ════════════════════════════════════════════════════
   分隔线
════════════════════════════════════════════════════ */
hr {
    border-color: var(--border) !important;
    margin: 16px 0 !important;
}

/* ════════════════════════════════════════════════════
   标题层级
════════════════════════════════════════════════════ */
h1 { font-weight: 800 !important; color: var(--text-1) !important; letter-spacing: -.5px; }
h2 { font-weight: 700 !important; color: var(--text-1) !important; font-size: 1.3rem !important; }
h3 { font-weight: 600 !important; color: var(--text-1) !important; font-size: 1.05rem !important; }

/* ════════════════════════════════════════════════════
   Checkbox / Radio
════════════════════════════════════════════════════ */
.stCheckbox label, .stRadio label {
    font-size: 0.875rem !important;
    color: var(--text-1) !important;
}
</style>
""", unsafe_allow_html=True)

# ── 默认配置模板 ──────────────────────────────────────────────────────────────
_DEFAULT_CLUSTER = {
    'connection_type': 'kubeconfig',
    'kubeconfig_path': os.environ.get('KUBECONFIG', os.path.expanduser('~/.kube/config')),
    'api_server': '',
    'token': '',
    'ca_cert': '',
    'connected': False,
    'cluster_info': {},
    'profile_name': '',
}
_DEFAULT_MONITOR = {
    'prometheus_url': os.environ.get('PROMETHEUS_URL', 'http://localhost:9090'),
    'username': '',
    'password': '',
    'profile_name': '',
}
_DEFAULT_GRAFANA = {
    'grafana_url': os.environ.get('GRAFANA_URL', 'http://localhost:3000'),
    'grafana_api_key': '',
    'grafana_username': 'admin',
    'grafana_password': 'admin',
    'prometheus_datasource': 'Prometheus',
    'pushgateway_url': os.environ.get('PUSHGATEWAY_URL', 'http://localhost:9091'),
    'enabled': False,
}

# ── Session State 初始化 ───────────────────────────────────────────────────────
if 'drill_history' not in st.session_state:
    st.session_state.drill_history = db.load_drill_history()

if 'current_drill' not in st.session_state:
    st.session_state.current_drill = None

if 'chaos_injector' not in st.session_state:
    st.session_state.chaos_injector = None

if 'monitor_checker' not in st.session_state:
    st.session_state.monitor_checker = None

if 'cluster_config' not in st.session_state:
    saved = db.get_default_k8s_profile()
    st.session_state.cluster_config = {**_DEFAULT_CLUSTER, **(saved or {})}

if 'monitor_config' not in st.session_state:
    saved_mon = db.get_default_monitor_profile()
    st.session_state.monitor_config = {**_DEFAULT_MONITOR, **(saved_mon or {})}

if 'cluster_resources' not in st.session_state:
    st.session_state.cluster_resources = {'namespaces': [], 'pods': [], 'deployments': []}

if 'grafana_config' not in st.session_state:
    st.session_state.grafana_config = {**_DEFAULT_GRAFANA}

if 'grafana_integration' not in st.session_state:
    st.session_state.grafana_integration = None

if 'fi_pod_list' not in st.session_state:
    st.session_state.fi_pod_list = []   # pod names loaded for fault injection

if 'fi_pod_ns' not in st.session_state:
    st.session_state.fi_pod_ns = ''     # namespace for which pod list was loaded

if 'notify_config' not in st.session_state:
    st.session_state.notify_config = {
        'enabled': False,
        'webhook_url': '',
        'events': ['演练完成', '演练失败'],
    }

if 'fi_health_check_results' not in st.session_state:
    st.session_state.fi_health_check_results = None   # 上次健康预检结果

if 'fi_pending_drill_params' not in st.session_state:
    st.session_state.fi_pending_drill_params = None   # 等待确认的演练参数

if 'drill_task_id' not in st.session_state:
    st.session_state.drill_task_id = None             # 后台任务 ID

if 'drill_in_progress' not in st.session_state:
    st.session_state.drill_in_progress = False        # 是否有演练正在后台运行

# ── 自动连接标志 ───────────────────────────────────────────────────────────────
if 'auto_connect_done' not in st.session_state:
    st.session_state.auto_connect_done = False


def _try_auto_connect():
    """启动时自动连接集群和初始化监控（如果已保存配置）"""
    if st.session_state.auto_connect_done:
        return
    
    st.session_state.auto_connect_done = True
    
    # 自动连接 K8s 集群
    if st.session_state.chaos_injector is None:
        cfg = st.session_state.cluster_config
        # 检查配置是否完整
        conn_type = cfg.get('connection_type', 'kubeconfig').lower()
        can_connect = False
        
        if conn_type == 'token':
            api_server = cfg.get('api_server', '')
            token = cfg.get('token', '')
            if api_server and token:
                can_connect = True
        else:
            kubeconfig_path = cfg.get('kubeconfig_path', '')
            if kubeconfig_path:
                expanded = os.path.expanduser(kubeconfig_path)
                if os.path.exists(expanded):
                    can_connect = True
        
        if can_connect:
            try:
                injector = _build_injector(config=cfg, use_chaos_mesh=False)
                if injector:
                    # 测试连接
                    cluster_info = injector.get_cluster_info()
                    st.session_state.cluster_config['connected'] = True
                    st.session_state.cluster_config['cluster_info'] = cluster_info
                    st.session_state.chaos_injector = injector
            except Exception:
                # 自动连接失败不显示错误，用户可以手动连接
                pass
    
    # 自动初始化监控检查器
    if st.session_state.monitor_checker is None:
        mon_cfg = st.session_state.monitor_config
        prom_url = mon_cfg.get('prometheus_url', '')
        if prom_url:
            try:
                username = mon_cfg.get('username') or None
                password = mon_cfg.get('password') or None
                st.session_state.monitor_checker = MonitorChecker(prom_url, username, password)
            except Exception:
                pass


# ── 启动时执行自动连接 ─────────────────────────────────────────────────────────
_try_auto_connect()



def load_scenarios():
    """加载故障场景配置"""
    scenarios_dir = "scenarios"
    scenarios = []

    if os.path.exists(scenarios_dir):
        for filename in os.listdir(scenarios_dir):
            if filename.endswith('.yaml'):
                # 安全检查：防止路径遍历攻击
                if '..' in filename or '/' in filename or '\\' in filename:
                    continue

                filepath = os.path.join(scenarios_dir, filename)

                # 验证文件路径在预期目录内
                abs_scenarios_dir = os.path.abspath(scenarios_dir)
                abs_filepath = os.path.abspath(filepath)
                if not abs_filepath.startswith(abs_scenarios_dir):
                    continue

                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        config = yaml.safe_load(f)
                        if config and isinstance(config, dict):
                            scenario = config.get('scenario', {})
                            scenarios.append({
                                'filename': filename,
                                'name': scenario.get('name', filename),
                                'description': scenario.get('description', ''),
                                'type': scenario.get('type', 'unknown')
                            })
                except Exception as e:
                    # 记录错误但继续加载其他场景
                    st.warning(f"加载场景文件 {filename} 失败: {e}")
                    continue

    return scenarios


def _build_injector(config=None, use_chaos_mesh=False):
    """从配置字典构建 ChaosInjector，成功返回实例，配置不完整或文件缺失返回 None"""
    cfg = config if config is not None else st.session_state.cluster_config
    conn_type = cfg.get('connection_type', 'kubeconfig').lower()
    if conn_type == 'token':
        api_server = cfg.get('api_server', '')
        token = cfg.get('token', '')
        if not api_server or not token:
            return None
        return ChaosInjector(
            use_chaos_mesh=use_chaos_mesh,
            cluster_api_server=api_server,
            cluster_token=token,
            cluster_ca_cert=cfg.get('ca_cert') or None,
        )
    else:
        kubeconfig_path = cfg.get('kubeconfig_path', os.path.expanduser('~/.kube/config'))
        expanded = os.path.expanduser(kubeconfig_path) if kubeconfig_path else ''
        if not expanded or not os.path.exists(expanded):
            return None
        return ChaosInjector(use_chaos_mesh=use_chaos_mesh, kubeconfig_path=kubeconfig_path)


def _do_k8s_connect():
    """测试并建立 k8s 连接，成功后自动初始化故障注入器"""
    config = st.session_state.cluster_config
    conn_type = config.get('connection_type', 'kubeconfig').lower()
    try:
        if conn_type == 'token':
            api_server_val = config.get('api_server', '')
            token_val = config.get('token', '')
            if not api_server_val or not token_val:
                st.error("请填写 API Server 地址和 Token")
                return
            test_injector = ChaosInjector(
                cluster_api_server=api_server_val,
                cluster_token=token_val,
                cluster_ca_cert=config.get('ca_cert') or None,
            )
        else:
            kp = config.get('kubeconfig_path', os.path.expanduser('~/.kube/config'))
            if not os.path.exists(os.path.expanduser(kp)):
                st.error("Kubeconfig 文件不存在")
                return
            test_injector = ChaosInjector(kubeconfig_path=kp)

        cluster_info = test_injector.get_cluster_info()
        st.session_state.cluster_config['connected'] = True
        st.session_state.cluster_config['cluster_info'] = cluster_info
        # 连接成功后直接复用此实例，无需二次初始化
        st.session_state.chaos_injector = test_injector
        st.success("✓ 集群连接成功，故障注入器已就绪！")
        if cluster_info.get('_errors'):
            st.warning("部分集群信息获取失败（不影响使用）")
    except Exception as e:
        st.error(f"✗ 连接失败: {e}")
        st.session_state.cluster_config['connected'] = False


def _save_k8s_profile_action(name):
    """保存当前 k8s 配置为档案并设为默认"""
    name = (name or '').strip()
    if not name:
        st.error("请输入档案名称")
        return
    ok = db.save_k8s_profile(name, st.session_state.cluster_config, set_default=True)
    if ok:
        st.success(f"✓ 已保存档案「{name}」")
        st.rerun()
    else:
        st.error("保存失败，请重试")


def init_chaos_injector(use_chaos_mesh=False, silent=False):
    """初始化故障注入器；silent=True 时不输出 st 消息"""
    if st.session_state.chaos_injector is not None:
        return True
    try:
        injector = _build_injector(use_chaos_mesh=use_chaos_mesh)
        if injector is None:
            if not silent:
                st.warning("⚠ 集群配置不完整，无法初始化故障注入器")
            return False
        st.session_state.chaos_injector = injector
        if not silent:
            st.success("✓ 故障注入器初始化成功")
        return True
    except Exception as e:
        if not silent:
            st.error(f"✗ 故障注入器初始化失败: {e}")
        return False


def init_monitor_checker(prometheus_url, username=None, password=None):
    """初始化监控验证器"""
    if st.session_state.monitor_checker is None:
        try:
            st.session_state.monitor_checker = MonitorChecker(prometheus_url, username, password)
            st.success("✓ 监控验证器初始化成功")
            return True
        except Exception as e:
            st.error(f"✗ 监控验证器初始化失败: {e}")
            return False
    return True


# 旧的 _try_auto_init 函数已被 _try_auto_connect 替代


def validate_input(input_str, field_name, max_length=253):
    """
    验证输入字符串

    参数：
        input_str: 输入字符串
        field_name: 字段名称
        max_length: 最大长度

    返回：
        tuple: (是否有效, 错误消息)
    """
    if not input_str or not input_str.strip():
        return False, f"{field_name}不能为空"

    # 检查长度
    if len(input_str) > max_length:
        return False, f"{field_name}长度不能超过 {max_length} 个字符"

    # 检查 Kubernetes 资源名称规则（小写字母、数字、连字符）
    import re
    if not re.match(r'^[a-z0-9]([-a-z0-9]*[a-z0-9])?$', input_str):
        return False, f"{field_name}只能包含小写字母、数字和连字符，且必须以字母或数字开头和结尾"

    return True, ""


def _run_health_check(namespace: str, pod_name: str, scenario_type: str) -> list[dict]:
    """
    演练前健康预检，返回检查项列表。
    每项格式: {'name': str, 'status': 'pass'|'warn'|'fail', 'message': str}
    """
    injector = st.session_state.chaos_injector
    monitor = st.session_state.monitor_checker
    results = []

    # ── 1. 命名空间是否存在 ────────────────────────────────────────
    try:
        namespaces = injector.list_namespaces()
        if namespace in namespaces:
            results.append({'name': '命名空间存在', 'status': 'pass', 'message': f'Namespace "{namespace}" 已找到'})
        else:
            results.append({'name': '命名空间存在', 'status': 'fail', 'message': f'Namespace "{namespace}" 不存在，可用命名空间: {", ".join(namespaces[:8])}'})
    except Exception as e:
        results.append({'name': '命名空间存在', 'status': 'warn', 'message': f'无法查询命名空间列表: {e}'})

    # ── 2. Pod 是否存在且处于 Running 状态 ────────────────────────
    try:
        pods = injector.list_pods(namespace)
        matched = [p for p in pods if p['name'] == pod_name]
        if not matched:
            results.append({'name': 'Pod 状态', 'status': 'fail', 'message': f'Pod "{pod_name}" 在命名空间 "{namespace}" 中不存在'})
        else:
            pod_status = matched[0].get('status', 'Unknown')
            if pod_status == 'Running':
                results.append({'name': 'Pod 状态', 'status': 'pass', 'message': f'Pod "{pod_name}" 当前状态: Running ✓'})
            else:
                results.append({'name': 'Pod 状态', 'status': 'fail', 'message': f'Pod "{pod_name}" 当前状态: {pod_status}，不建议注入故障'})
    except Exception as e:
        results.append({'name': 'Pod 状态', 'status': 'warn', 'message': f'无法查询 Pod 状态: {e}'})

    # ── 3. pod_crash 场景：检查是否有 Deployment 托管该 Pod ────────
    if scenario_type == 'pod_crash':
        try:
            deployments = injector.list_deployments(namespace)
            pods = injector.list_pods(namespace)
            matched = [p for p in pods if p['name'] == pod_name]
            has_owner = False
            if matched:
                # Pod 名称通常为 <deployment>-<rs-hash>-<pod-hash>，检查是否有匹配的 Deployment
                for dep in deployments:
                    if pod_name.startswith(dep['name'] + '-'):
                        has_owner = True
                        results.append({'name': 'Deployment 托管检查', 'status': 'pass', 'message': f'Pod 由 Deployment "{dep["name"]}" 托管，崩溃后可自动恢复'})
                        break
            if not has_owner:
                results.append({'name': 'Deployment 托管检查', 'status': 'warn', 'message': 'Pod 可能不受 Deployment 托管，pod_crash 后可能无法自动恢复'})
        except Exception as e:
            results.append({'name': 'Deployment 托管检查', 'status': 'warn', 'message': f'无法验证 Deployment 托管关系: {e}'})

    # ── 4. 是否已有活跃告警（避免干扰基线）─────────────────────────
    if monitor is not None:
        try:
            alerts = monitor.prometheus.query_alerts()
            if alerts:
                alert_names = [a.get('labels', {}).get('alertname', '未知') for a in alerts[:5]]
                results.append({'name': '活跃告警基线', 'status': 'warn',
                                'message': f'当前已有 {len(alerts)} 个活跃告警（{", ".join(alert_names)}），可能干扰演练结果判断'})
            else:
                results.append({'name': '活跃告警基线', 'status': 'pass', 'message': '当前无活跃告警，基线干净'})
        except Exception as e:
            results.append({'name': '活跃告警基线', 'status': 'warn', 'message': f'无法查询 Prometheus 告警: {e}'})
    else:
        results.append({'name': '活跃告警基线', 'status': 'warn', 'message': '监控未配置，跳过告警基线检查'})

    return results


def _display_health_check(check_results: list[dict]) -> bool:
    """
    展示健康预检结果，返回是否存在 fail 级别的检查项。
    """
    icon_map = {'pass': '✅', 'warn': '⚠️', 'fail': '❌'}
    color_map = {'pass': 'status-success', 'warn': 'status-warning', 'fail': 'status-error'}

    has_fail = any(r['status'] == 'fail' for r in check_results)

    with st.expander("🩺 演练前健康预检结果", expanded=True):
        for item in check_results:
            icon = icon_map[item['status']]
            css = color_map[item['status']]
            st.markdown(
                f"{icon} **{item['name']}**  "
                f"<span class='{css}'>{item['message']}</span>",
                unsafe_allow_html=True,
            )
        if has_fail:
            st.error("❌ 存在关键检查项未通过，建议修复后再执行演练。如确认要强制执行，请勾选下方选项。")
        else:
            st.success("✅ 所有关键检查通过，可以开始演练")

    return has_fail


def _execute_drill(params: dict):
    """执行演练的核心逻辑（供健康预检通过后直接调用 or 强制确认后调用）"""
    _CHAOS_MESH_SCENARIOS = {'cpu_stress', 'network_delay', 'disk_io', 'memory_stress'}
    namespace = params['namespace']
    safe_pod = params['pod_name']
    scenario = params['scenario']
    timeout = params['timeout']
    duration_str = params['duration_str']
    scenario_type = scenario['type']
    check_interval = params.get('check_interval', 5)

    with st.spinner("正在执行演练..."):
        start_time = datetime.now()
        result = None

        try:
            if scenario_type == 'pod_crash':
                result = st.session_state.chaos_injector.delete_pod(namespace, safe_pod)

            elif scenario_type == 'cpu_stress':
                result = st.session_state.chaos_injector.inject_cpu_stress(
                    namespace=namespace,
                    pod_name=safe_pod,
                    cpu_workers=params.get('cpu_workers', 1),
                    cpu_load=params.get('cpu_load', 100),
                    duration=duration_str,
                )
            elif scenario_type == 'network_delay':
                result = st.session_state.chaos_injector.inject_network_delay(
                    namespace=namespace,
                    pod_name=safe_pod,
                    latency=params.get('net_latency', '100ms'),
                    jitter=params.get('net_jitter', '10ms'),
                    duration=duration_str,
                )
            elif scenario_type == 'disk_io':
                result = st.session_state.chaos_injector.inject_disk_failure(
                    namespace=namespace,
                    pod_name=safe_pod,
                    path=params.get('disk_path', '/var/log'),
                    fault_type=params.get('disk_fault_type', 'disk_fill'),
                    size=params.get('disk_size', '1Gi'),
                    duration=duration_str,
                )
            elif scenario_type == 'memory_stress':
                result = st.session_state.chaos_injector.inject_memory_stress(
                    namespace=namespace,
                    pod_name=safe_pod,
                    memory_size=params.get('memory_size', '256Mi'),
                    memory_workers=params.get('memory_workers', 1),
                    duration=duration_str,
                )
            else:
                st.error(f"未知的场景类型: {scenario_type}")
                return

            # Chaos Mesh 场景：资源已提交，需在客户端等待实际持续时间
            if result and result.get('success') and scenario_type in _CHAOS_MESH_SCENARIOS:
                progress_bar = st.progress(0.0)
                status_ph = st.empty()
                elapsed = 0
                while elapsed < timeout:
                    step = min(check_interval, timeout - elapsed)
                    time.sleep(step)
                    elapsed += step
                    progress_bar.progress(elapsed / timeout)
                    status_ph.caption(f"⏱ 压测进行中 {elapsed}/{timeout} 秒…")
                status_ph.caption(f"✓ 压测已持续 {timeout} 秒，Chaos Mesh 正在自动清理资源")

            end_time = datetime.now()
            drill_duration = (end_time - start_time).total_seconds()

            # 记录演练历史
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
            st.session_state.drill_history.append(_entry)
            db.append_drill_history(_entry)

            # 发送通知
            notify_event = '演练完成' if result.get('success', False) else '演练失败'
            _send_notification(notify_event, {
                'scenario': scenario['name'],
                'namespace': namespace,
                'pod_name': safe_pod,
                'status': _entry['status'],
                'duration': _entry['duration'],
            })

            # 生成演练报告
            _generate_drill_report(
                scenario=scenario,
                namespace=namespace,
                pod_name=safe_pod,
                start_time=start_time,
                end_time=end_time,
                drill_duration=drill_duration,
                result=result,
            )

            # 显示演练结果
            st.markdown("---")
            st.subheader("📊 演练结果")
            result_data = {
                '场景名称': scenario['name'],
                '故障类型': scenario['type'],
                '命名空间': namespace,
                'Pod 名称': safe_pod,
                '演练状态': '<span class="status-success">成功</span>' if result.get('success', False) else '<span class="status-error">失败</span>',
                '耗时': f'{drill_duration:.2f} 秒',
                '完成时间': end_time.strftime('%Y-%m-%d %H:%M:%S'),
            }
            for key, value in result_data.items():
                st.markdown(f"**{key}**: {value}", unsafe_allow_html=True)

            if result.get('recovery_time'):
                st.info(f"📈 Pod 恢复时间: {result['recovery_time']} 秒")
            if result.get('message'):
                st.info(f"💬 消息: {result['message']}")

        except Exception as e:
            st.error(f"❌ 演练执行出错: {e}")
            import traceback
            st.error(traceback.format_exc())


def _run_drill_background(params: dict, task_id: str, injector, notify_cfg: dict):
    """在后台线程执行演练核心逻辑（无任何 st.* 调用）。结果写入 _drill_tasks[task_id]。"""
    _CHAOS_MESH_SCENARIOS = {'cpu_stress', 'network_delay', 'disk_io', 'memory_stress'}
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
            with _drill_tasks_lock:
                _drill_tasks[task_id] = {'status': 'error', 'error_msg': f'未知的场景类型: {scenario_type}'}
            return

        # Chaos Mesh 场景：等待实际持续时间，并定期更新进度
        _CHAOS_TYPE_MAP = {
            'cpu_stress': 'stress', 'memory_stress': 'stress',
            'network_delay': 'network_delay', 'disk_io': 'io',
        }
        stopped = False
        if result and result.get('success') and scenario_type in _CHAOS_MESH_SCENARIOS:
            elapsed = 0
            while elapsed < timeout:
                step = min(check_interval, timeout - elapsed)
                time.sleep(step)
                elapsed += step
                with _drill_tasks_lock:
                    _drill_tasks[task_id]['elapsed'] = elapsed
                    _drill_tasks[task_id]['total'] = timeout
                    if _drill_tasks[task_id].get('stop_signal'):
                        stopped = True
                        break

            if stopped:
                # 清理 Chaos Mesh 资源
                chaos_type_key = _CHAOS_TYPE_MAP.get(scenario_type)
                chaos_name = result.get('chaos_name', '')
                if chaos_type_key and chaos_name and hasattr(injector, 'chaos_mesh') and injector.chaos_mesh:
                    try:
                        injector.chaos_mesh.delete_chaos(namespace, chaos_name, chaos_type_key)
                    except Exception:
                        pass
                with _drill_tasks_lock:
                    _drill_tasks[task_id].update({'status': 'stopped'})
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

        notify_event = '演练完成' if result.get('success', False) else '演练失败'
        _send_notification(notify_event, {
            'scenario': scenario['name'],
            'namespace': namespace,
            'pod_name': safe_pod,
            'status': _entry['status'],
            'duration': _entry['duration'],
        }, notify_cfg)

        _generate_drill_report(
            scenario=scenario,
            namespace=namespace,
            pod_name=safe_pod,
            start_time=start_time,
            end_time=end_time,
            drill_duration=drill_duration,
            result=result,
        )

        with _drill_tasks_lock:
            _drill_tasks[task_id].update({
                'status': 'done',
                'result': result,
                'entry': _entry,
                'drill_duration': drill_duration,
                'end_time_str': end_time.strftime('%Y-%m-%d %H:%M:%S'),
            })

    except Exception as exc:
        import traceback as _tb
        with _drill_tasks_lock:
            _drill_tasks[task_id] = {
                'status': 'error',
                'error_msg': str(exc),
                'traceback': _tb.format_exc(),
            }


def _start_drill_thread(params: dict):
    """启动后台演练线程，立即返回。调用方应在之后调用 st.rerun()。"""
    task_id = uuid.uuid4().hex[:8]
    injector = st.session_state.chaos_injector
    notify_cfg = dict(st.session_state.notify_config)

    with _drill_tasks_lock:
        _drill_tasks[task_id] = {
            'status': 'running',
            'elapsed': 0,
            'total': params.get('timeout', 60),
            'scenario_name': params['scenario']['name'],
        }

    t = threading.Thread(
        target=_run_drill_background,
        args=(params, task_id, injector, notify_cfg),
        daemon=True,
    )
    t.start()

    st.session_state.drill_task_id = task_id
    st.session_state.drill_in_progress = True


def _run_chain_drill_background(task_id: str, chain_name: str, stages: list, injector, notify_cfg: dict):
    """在后台线程顺序执行多步骤故障链（无 st.* 调用）"""
    _CHAOS_TYPE_MAP = {
        'cpu_stress': 'stress', 'memory_stress': 'stress',
        'network_delay': 'network_delay', 'disk_io': 'io',
    }
    start_time = datetime.now()
    log_entries = []

    def _log(msg):
        ts = datetime.now().strftime('%H:%M:%S')
        log_entries.append(f'[{ts}] {msg}')
        with _drill_tasks_lock:
            _drill_tasks[task_id]['log'] = list(log_entries)

    try:
        for idx, stage in enumerate(stages):
            with _drill_tasks_lock:
                if _drill_tasks[task_id].get('stop_signal'):
                    _log(f'⛔ 用户中断，在 Stage {idx + 1} 前停止')
                    _drill_tasks[task_id]['status'] = 'stopped'
                    return
                _drill_tasks[task_id]['current_stage'] = idx + 1
                _drill_tasks[task_id]['total_stages'] = len(stages)

            stype = stage.get('type', 'wait')
            _log(f'▶ Stage {idx + 1}/{len(stages)}: {stype}')

            if stype == 'wait':
                wait_sec = int(stage.get('wait_seconds', 10))
                _log(f'  等待 {wait_sec} 秒...')
                elapsed_w = 0
                while elapsed_w < wait_sec:
                    time.sleep(min(2, wait_sec - elapsed_w))
                    elapsed_w += 2
                    with _drill_tasks_lock:
                        if _drill_tasks[task_id].get('stop_signal'):
                            _log('⛔ 用户中断等待阶段')
                            _drill_tasks[task_id]['status'] = 'stopped'
                            return
                _log(f'  ✓ 等待完成')

            elif stype == 'verify_alert':
                import requests as _req
                alert_name = stage.get('alert_name', '')
                expected = stage.get('expected', 'firing')
                prom = st.session_state.get('monitor_checker') if hasattr(st, 'session_state') else None
                # 直接查询 Prometheus alerts API
                try:
                    mon_profile = db.get_default_monitor_profile()
                    prom_url = mon_profile.get('prometheus_url', '') if mon_profile else ''
                    resp = _req.get(f'{prom_url}/api/v1/alerts', timeout=5)
                    alerts_data = resp.json().get('data', {}).get('alerts', [])
                    firing = any(
                        a.get('labels', {}).get('alertname') == alert_name and a.get('state') == 'firing'
                        for a in alerts_data
                    )
                    ok = (firing and expected == 'firing') or (not firing and expected == 'resolved')
                    _log(f'  告警 {alert_name} 状态: {"触发" if firing else "未触发"} — {"✓ 符合预期" if ok else "✗ 不符合预期"}')
                except Exception as e:
                    _log(f'  ✗ 查询告警失败: {e}')

            elif stype == 'fault':
                scenario_type = stage.get('scenario', 'cpu_stress')
                namespace = stage.get('namespace', 'default')
                pod_selector = stage.get('pod_selector', '')
                duration = int(stage.get('duration', 60))
                duration_str = f'{duration}s'

                scenario_map = {
                    'cpu_stress': {'type': 'cpu_stress', 'name': 'CPU 压力测试'},
                    'memory_stress': {'type': 'memory_stress', 'name': '内存压力测试'},
                    'network_delay': {'type': 'network_delay', 'name': '网络延迟'},
                    'disk_io': {'type': 'disk_io', 'name': '磁盘 IO'},
                    'pod_crash': {'type': 'pod_crash', 'name': 'Pod 崩溃'},
                }
                scenario = scenario_map.get(scenario_type, {'type': scenario_type, 'name': scenario_type})

                try:
                    if scenario_type == 'pod_crash':
                        result = injector.delete_pod(namespace, pod_selector)
                    elif scenario_type == 'cpu_stress':
                        result = injector.inject_cpu_stress(
                            namespace=namespace, pod_name=pod_selector,
                            cpu_workers=stage.get('cpu_workers', 1),
                            cpu_load=stage.get('cpu_load', 100),
                            duration=duration_str,
                        )
                    elif scenario_type == 'memory_stress':
                        result = injector.inject_memory_stress(
                            namespace=namespace, pod_name=pod_selector,
                            memory_size=stage.get('memory_size', '256Mi'),
                            memory_workers=stage.get('memory_workers', 1),
                            duration=duration_str,
                        )
                    elif scenario_type == 'network_delay':
                        result = injector.inject_network_delay(
                            namespace=namespace, pod_name=pod_selector,
                            latency=stage.get('net_latency', '100ms'),
                            jitter=stage.get('net_jitter', '10ms'),
                            duration=duration_str,
                        )
                    elif scenario_type == 'disk_io':
                        result = injector.inject_disk_failure(
                            namespace=namespace, pod_name=pod_selector,
                            path=stage.get('disk_path', '/var/log'),
                            fault_type=stage.get('disk_fault_type', 'disk_fill'),
                            size=stage.get('disk_size', '1Gi'),
                            duration=duration_str,
                        )
                    else:
                        result = {'success': False, 'message': f'未知场景: {scenario_type}'}

                    if result and result.get('success') and scenario_type in {'cpu_stress', 'memory_stress', 'network_delay', 'disk_io'}:
                        _log(f'  ✓ 故障注入成功，等待 {duration}s ...')
                        elapsed_f = 0
                        chaos_name = result.get('chaos_name', '')
                        while elapsed_f < duration:
                            time.sleep(min(5, duration - elapsed_f))
                            elapsed_f += 5
                            with _drill_tasks_lock:
                                if _drill_tasks[task_id].get('stop_signal'):
                                    # 清理 Chaos Mesh
                                    ct = _CHAOS_TYPE_MAP.get(scenario_type)
                                    if ct and chaos_name and hasattr(injector, 'chaos_mesh') and injector.chaos_mesh:
                                        try:
                                            injector.chaos_mesh.delete_chaos(namespace, chaos_name, ct)
                                        except Exception:
                                            pass
                                    _log('⛔ 用户中断故障等待阶段')
                                    _drill_tasks[task_id]['status'] = 'stopped'
                                    return
                        _log(f'  ✓ 故障持续完成')
                    else:
                        _log(f'  ✗ 故障注入失败: {result.get("message", "") if result else "无返回"}')
                except Exception as e:
                    _log(f'  ✗ Stage 异常: {e}')

        end_time = datetime.now()
        drill_duration = (end_time - start_time).total_seconds()
        entry = {
            'time': start_time.strftime('%Y-%m-%d %H:%M:%S'),
            'scenario': f'[故障链] {chain_name}',
            'status': '成功',
            'duration': round(drill_duration, 2),
            'message': f'{len(stages)} 个 stage 全部完成',
        }
        db.append_drill_history(entry)
        _log(f'✅ 故障链执行完毕，耗时 {drill_duration:.1f}s')
        with _drill_tasks_lock:
            _drill_tasks[task_id].update({'status': 'done', 'entry': entry, 'drill_duration': drill_duration})

    except Exception as exc:
        import traceback as _tb
        _log(f'✗ 异常: {exc}')
        with _drill_tasks_lock:
            _drill_tasks[task_id].update({
                'status': 'error',
                'error_msg': str(exc),
                'traceback': _tb.format_exc(),
            })
    """发送 Webhook 通知（异步，失败不影响主流程）"""
    cfg = _cfg if _cfg is not None else st.session_state.notify_config
    if not cfg.get('enabled'):
        return
    if event not in cfg.get('events', []):
        return
    url = cfg.get('webhook_url', '').strip()
    if not url:
        return
    import requests as _req
    try:
        payload = {
            'event': event,
            'platform': 'EDAP',
            'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            **data,
        }
        _req.post(url, json=payload, timeout=5)
    except Exception:
        pass  # 通知失败静默处理，不影响演练流程


def page_home():
    """首页"""
    st.markdown('<h1 class="main-header">应急演练智能平台</h1>', unsafe_allow_html=True)
    st.markdown('<p style="text-align:center;color:#94A3B8;font-size:.9rem;margin-top:-8px;margin-bottom:20px;">Emergency Drill Platform</p>', unsafe_allow_html=True)

    # ── 统计卡片 ──
    total   = len(st.session_state.drill_history)
    success = len([d for d in st.session_state.drill_history if d.get('status') == '成功'])
    rate    = f"{success / total * 100:.1f}%" if total else "—"
    n_scene = len(load_scenarios())
    avg_dur = 0
    if total:
        durs = [d.get('duration', 0) for d in st.session_state.drill_history if d.get('duration')]
        avg_dur = sum(durs) / len(durs) if durs else 0

    c1, c2, c3, c4 = st.columns(4)
    for col, icon, val, label, sub, color in [
        (c1, "📋", str(total),    "演练次数",   f"成功 {success} 次",          "blue"),
        (c2, "✅", rate,          "成功率",     f"{success}/{total}",          "green"),
        (c3, "⚡", str(n_scene),  "可用场景",   "故障注入场景总数",              "amber"),
        (c4, "⏱️", f"{avg_dur:.1f}s", "平均耗时", "所有演练平均持续时间",        "red"),
    ]:
        with col:
            st.markdown(f"""
<div class="metric-card {color}">
  <span class="mc-icon">{icon}</span>
  <div class="mc-value">{val}</div>
  <div class="mc-label">{label}</div>
  <div class="mc-sub">{sub}</div>
</div>""", unsafe_allow_html=True)

    st.markdown("---")

    # ── 快速操作 ──
    st.markdown('<div class="section-title">快速操作</div>', unsafe_allow_html=True)
    qa1, qa2, qa3, qa4 = st.columns(4)
    with qa1:
        if st.button("⚡ 故障注入演练", use_container_width=True, type="primary"):
            st.session_state.page = "fault_injection"
            st.rerun()
    with qa2:
        if st.button("🔗 多步骤故障链", use_container_width=True):
            st.session_state.page = "chain_drill"
            st.rerun()
    with qa3:
        if st.button("📊 监控面板", use_container_width=True):
            st.session_state.page = "monitor"
            st.rerun()
    with qa4:
        if st.button("⚙️ 系统设置", use_container_width=True):
            st.session_state.page = "settings"
            st.rerun()

    st.markdown("---")

    # ── 即将执行的演练计划 ──
    if _SCHEDULER_AVAILABLE:
        all_schedules = db.list_drill_schedules()
        upcoming = sorted(
            [s for s in all_schedules if s.get('enabled') and s.get('next_run')],
            key=lambda x: x['next_run']
        )[:5]
        with st.expander(f"📅 即将执行的演练计划（{len(upcoming)} 条）", expanded=bool(upcoming)):
            if upcoming:
                for s in upcoming:
                    st.markdown(
                        f'<span class="badge badge-info">{s["scenario"]}</span>&nbsp;'
                        f'<b>{s["name"]}</b> &nbsp;<code>{s["cron_expr"]}</code>'
                        f'&nbsp;→ 下次执行：<code>{s["next_run"]}</code>',
                        unsafe_allow_html=True
                    )
            else:
                st.info("暂无已启用的演练计划。前往 ⚙️ 设置 → 🗓️ 演练计划 添加。")

    # ── 演练历史 ──
    st.markdown('<div class="section-title">最近演练记录</div>', unsafe_allow_html=True)

    if st.session_state.drill_history:
        df = pd.DataFrame(st.session_state.drill_history)
        if not df.empty:
            display_cols = ['time', 'scenario', 'status', 'duration']
            if all(col in df.columns for col in display_cols):
                df_display = df[display_cols].copy()
                df_display.columns = ['时间', '场景', '状态', '耗时(秒)']
                st.dataframe(df_display, use_container_width=True, hide_index=True)
            else:
                st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("暂无演练记录，请先执行演练")


def page_cluster_resources():
    """集群资源浏览页面"""
    st.title("🗂️ 集群资源")

    injector = st.session_state.chaos_injector
    if injector is None:
        st.warning("⚠ 集群未连接，请先在「⚙️ 设置」页面配置并连接集群")
        return

    # ── 顶部工具栏 ────────────────────────────────────────────────────────────
    col_ns, col_filter, col_refresh = st.columns([2, 3, 1])

    with col_refresh:
        refresh = st.button("🔄 刷新", use_container_width=True)

    # 获取命名空间列表
    try:
        all_namespaces = injector.list_namespaces()
    except Exception as e:
        st.error(f"无法获取命名空间列表: {e}")
        return

    with col_ns:
        selected_ns = st.selectbox(
            "命名空间",
            ["（全部）"] + all_namespaces,
            label_visibility="collapsed",
            key="cr_namespace",
        )

    with col_filter:
        filter_text = st.text_input(
            "过滤",
            placeholder="输入关键词过滤 Pod/Deployment 名称",
            label_visibility="collapsed",
            key="cr_filter",
        )

    # 确定要查询的命名空间列表
    ns_list = all_namespaces if selected_ns == "（全部）" else [selected_ns]

    # ── 汇总指标 ─────────────────────────────────────────────────────────────
    all_pods: list[dict] = []
    all_deps: list[dict] = []
    load_errors: list[str] = []

    for ns in ns_list:
        try:
            pods = injector.list_pods(ns)
            all_pods.extend(pods)
        except Exception as e:
            load_errors.append(f"[{ns}] 获取 Pod 失败: {e}")
        try:
            deps = injector.list_deployments(ns)
            all_deps.extend(deps)
        except Exception as e:
            load_errors.append(f"[{ns}] 获取 Deployment 失败: {e}")

    if load_errors:
        for err in load_errors:
            st.warning(err)

    # 过滤
    kw = filter_text.strip().lower()
    filtered_pods = [p for p in all_pods if not kw or kw in p['name'].lower()]
    filtered_deps = [d for d in all_deps if not kw or kw in d['name'].lower()]

    # 汇总统计
    running_pods = [p for p in filtered_pods if p.get('status') == 'Running']
    not_running = [p for p in filtered_pods if p.get('status') != 'Running']

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Pod 总数", len(filtered_pods))
    m2.metric("Running", len(running_pods), delta=f"✓" if not_running == [] else None)
    m3.metric("非 Running", len(not_running))
    m4.metric("Deployment", len(filtered_deps))

    st.markdown("---")

    # ── Pod 列表 ──────────────────────────────────────────────────────────────
    tab_pods, tab_deps = st.tabs(["🟢 Pod 列表", "📦 Deployment 列表"])

    with tab_pods:
        if not filtered_pods:
            st.info("没有找到 Pod")
        else:
            # 状态图标
            status_icon = {
                'Running': '🟢',
                'Pending': '🟡',
                'Succeeded': '✅',
                'Failed': '🔴',
                'Unknown': '⚫',
                'Terminating': '🟠',
            }

            # 构建表格数据
            rows = []
            for p in filtered_pods:
                st_raw = p.get('status', 'Unknown')
                icon = status_icon.get(st_raw, '⚫')
                rows.append({
                    '状态': f"{icon} {st_raw}",
                    'Pod 名称': p['name'],
                    '节点': p.get('node', '-'),
                    '创建时间': p.get('created', '-'),
                })

            df_pods = pd.DataFrame(rows)
            st.dataframe(df_pods, use_container_width=True, hide_index=True)

            # 详情展开 - 按状态分组
            if not_running:
                with st.expander(f"⚠️ 非 Running Pod ({len(not_running)} 个)", expanded=True):
                    for p in not_running:
                        st_raw = p.get('status', 'Unknown')
                        icon = status_icon.get(st_raw, '⚫')
                        st.markdown(
                            f"{icon} **{p['name']}** — 状态: `{st_raw}` "
                            f"| 节点: `{p.get('node', '-')}`",
                        )

    with tab_deps:
        if not filtered_deps:
            st.info("没有找到 Deployment")
        else:
            rows_d = []
            for d in filtered_deps:
                replicas = d.get('replicas', 0)
                available = d.get('available_replicas', 0)
                health_icon = '🟢' if available == replicas and replicas > 0 else '🔴' if available == 0 else '🟡'
                rows_d.append({
                    '健康': health_icon,
                    'Deployment 名称': d['name'],
                    '命名空间': d.get('namespace', '-'),
                    '期望副本': replicas,
                    '可用副本': available,
                })

            df_deps = pd.DataFrame(rows_d)
            st.dataframe(df_deps, use_container_width=True, hide_index=True)

    # 强制刷新（将刷新结果写入 session state，触发下一次重新渲染）
    if refresh:
        st.rerun()


def page_fault_injection():
    """故障注入页面"""
    st.title("⚡ 故障注入")

    # ── 后台演练进行中：轮询并展示状态 ────────────────────────────────────────────
    if st.session_state.drill_in_progress:
        task_id = st.session_state.drill_task_id
        with _drill_tasks_lock:
            task = dict(_drill_tasks.get(task_id, {}))

        if not task:
            # 任务丢失（如进程重启），重置状态
            st.session_state.drill_in_progress = False
            st.session_state.drill_task_id = None

        elif task['status'] == 'running':
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
            # 将历史记录同步回 session state（后台线程已写入 DB）
            entry = task.get('entry', {})
            if entry:
                st.session_state.drill_history.append(entry)
            # 展示结果
            result = task.get('result', {})
            st.markdown("---")
            st.subheader("📊 演练结果")
            result_data = {
                '场景名称': entry.get('scenario', ''),
                '故障类型': entry.get('scenario_type', ''),
                '命名空间': entry.get('namespace', ''),
                'Pod 名称': entry.get('pod_name', ''),
                '演练状态': '<span class="status-success">成功</span>' if result.get('success') else '<span class="status-error">失败</span>',
                '耗时': f"{entry.get('duration', 0):.2f} 秒",
                '完成时间': task.get('end_time_str', ''),
            }
            for key, value in result_data.items():
                st.markdown(f"**{key}**: {value}", unsafe_allow_html=True)
            if result.get('recovery_time'):
                st.info(f"📈 Pod 恢复时间: {result['recovery_time']} 秒")
            if result.get('message'):
                st.info(f"💬 消息: {result['message']}")
            with _drill_tasks_lock:
                _drill_tasks.pop(task_id, None)
            st.markdown("---")

        elif task['status'] == 'error':
            st.session_state.drill_in_progress = False
            st.session_state.drill_task_id = None
            st.error(f"❌ 演练执行出错: {task.get('error_msg', '未知错误')}")
            if task.get('traceback'):
                with st.expander("详细错误"):
                    st.code(task['traceback'])
            with _drill_tasks_lock:
                _drill_tasks.pop(task_id, None)

    # 若注入器未就绪则尝试自动初始化（利用已保存的集群配置）
    if st.session_state.chaos_injector is None:
        init_chaos_injector(silent=True)

    if st.session_state.chaos_injector is None:
        st.warning("⚠ 集群未连接，请先在左侧导航「⚙️ 设置」页面配置并连接集群")
        return

    # ── 实时监控告警状态 ─────────────────────────────────────────────────────────
    st.subheader("📊 实时监控告警状态")
    
    if st.session_state.monitor_checker is None:
        st.warning("⚠ 监控未连接，请先在设置页面配置 Prometheus")
    else:
        try:
            # 获取告警数据
            alerts = st.session_state.monitor_checker.prometheus.query_alerts()
            
            col_alert1, col_alert2 = st.columns(2)
            
            with col_alert1:
                firing_count = len([a for a in alerts if a.get('state') == 'firing'])
                st.metric("触发告警", firing_count)
            
            with col_alert2:
                pending_count = len([a for a in alerts if a.get('state') == 'pending'])
                st.metric("待处理告警", pending_count)
            
            # 显示告警详情
            if alerts:
                with st.expander("📋 活跃告警列表", expanded=len(alerts) > 5):
                    for i, alert in enumerate(alerts[:10]):
                        alert_name = alert.get('labels', {}).get('alertname', 'N/A')
                        severity = alert.get('labels', {}).get('severity', 'N/A')
                        state = alert.get('state', 'N/A')
                        
                        st.write(f"**{alert_name}** | 严重性: {severity} | 状态: {state}")
                        
                        if alert.get('annotations'):
                            st.info(f"描述: {alert.get('annotations', {}).get('description', 'N/A')}")
            else:
                st.info("暂无活跃告警")
        except Exception as e:
            st.error(f"获取告警失败: {e}")
    
    st.markdown("---")

    # Chaos Mesh 开关（CPU 压测 / 网络延迟 / 磁盘故障 / 内存压力 需要）
    _CHAOS_MESH_SCENARIOS = {'cpu_stress', 'network_delay', 'disk_io', 'memory_stress'}
    current_cm = getattr(st.session_state.chaos_injector, 'use_chaos_mesh', False)
    use_chaos_mesh = st.checkbox(
        "使用 Chaos Mesh",
        value=current_cm,
        help="CPU 压测、网络延迟、磁盘故障场景需要 Chaos Mesh；Pod 崩溃场景不需要",
    )
    # 设置变化时重建注入器
    if use_chaos_mesh != current_cm:
        st.session_state.chaos_injector = None
        init_chaos_injector(use_chaos_mesh=use_chaos_mesh, silent=True)

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

    # 若所选场景需要 Chaos Mesh 但未启用，提前提示
    if scenario['type'] in _CHAOS_MESH_SCENARIOS and not use_chaos_mesh:
        st.warning(f"⚠ 「{scenario['name']}」需要 Chaos Mesh，请勾选上方「使用 Chaos Mesh」后再执行")

    st.markdown("---")
    
    # 参数配置
    st.subheader("🔧 参数配置")

    col1, col2 = st.columns(2)

    with col1:
        # 命名空间 + 刷新 Pod 按钮
        ns_col, ns_btn_col = st.columns([3, 1])
        with ns_col:
            namespace = st.text_input("命名空间", value="default")
        with ns_btn_col:
            st.markdown("<br>", unsafe_allow_html=True)  # 对齐按钮
            if st.button("📋 加载", help="从集群加载该命名空间的 Pod 列表", use_container_width=True):
                inj = st.session_state.chaos_injector
                if inj:
                    pods = inj.list_pods(namespace)
                    st.session_state.fi_pod_list = [p['name'] for p in pods]
                    st.session_state.fi_pod_ns = namespace
                    st.rerun()

        # Pod 选择方式
        pod_list = st.session_state.fi_pod_list
        if pod_list and st.session_state.fi_pod_ns == namespace:
            pod_name = st.selectbox(
                f"选择 Pod（{len(pod_list)} 个）",
                pod_list,
                help="点击上方「加载」按钮刷新列表",
            )
        else:
            pod_name = st.text_input("Pod 名称", placeholder="例如: nginx-deployment-xxx，或点击「加载」选择")
    
    with col2:
        timeout = st.number_input("超时时间(秒)", min_value=10, max_value=600, value=60)
        check_interval = st.number_input("检查间隔(秒)", min_value=1, max_value=30, value=5)
    
    # CPU 压测参数（仅当选择 CPU 压测场景时显示）
    if scenario['type'] == 'cpu_stress':
        st.markdown("#### ⚡ CPU 压测参数")
        col_stress1, col_stress2 = st.columns(2)
        
        with col_stress1:
            cpu_workers = st.number_input("CPU Workers", min_value=1, max_value=16, value=2,
                                          help="CPU 压测 worker 数量，每个 worker 会占用一个 CPU 核心")
        
        with col_stress2:
            cpu_load = st.number_input("CPU 负载 (%)", min_value=1, max_value=100, value=100,
                                       help="每个 CPU worker 的负载百分比")
    
    # 内存压测参数（仅当选择内存压测场景时显示）
    if scenario['type'] == 'memory_stress':
        st.markdown("#### 🧠 内存压测参数")
        col_stress1, col_stress2 = st.columns(2)

        with col_stress1:
            memory_size = st.text_input("内存大小", value="256Mi",
                                        help="内存压测大小，如 256Mi, 512Mi, 1Gi")

        with col_stress2:
            memory_workers = st.number_input("Memory Workers", min_value=1, max_value=8, value=1,
                                             help="内存压测 worker 数量")

    # 网络延迟参数（仅当选择网络延迟场景时显示）
    if scenario['type'] == 'network_delay':
        st.markdown("#### 🌐 网络延迟参数")
        col_net1, col_net2 = st.columns(2)
        with col_net1:
            net_latency = st.text_input("延迟时间", value="100ms",
                                        help="网络延迟，如 100ms, 500ms, 1s")
        with col_net2:
            net_jitter = st.text_input("抖动时间", value="10ms",
                                       help="延迟抖动范围，如 10ms, 50ms")

    # 磁盘 IO 参数（仅当选择磁盘故障场景时显示）
    if scenario['type'] == 'disk_io':
        st.markdown("#### 💾 磁盘故障参数")
        col_disk1, col_disk2 = st.columns(2)
        with col_disk1:
            disk_path = st.text_input("目标路径", value="/var/log",
                                      help="磁盘填充的目标路径")
            disk_size = st.text_input("填充大小", value="1Gi",
                                      help="disk_fill 时使用，如 512Mi, 1Gi")
        with col_disk2:
            disk_fault_type = st.selectbox(
                "故障类型",
                ["disk_fill", "disk_read_error", "disk_write_error"],
                help="disk_fill: 填充磁盘; disk_read_error: 读错误; disk_write_error: 写错误",
            )
    
    st.markdown("---")

    # ── 演练前健康预检结果（上次预检有失败项时展示确认区域）─────────────────────────
    if st.session_state.fi_health_check_results is not None:
        has_fail = _display_health_check(st.session_state.fi_health_check_results)
        if has_fail:
            force = st.checkbox("⚠️ 我了解风险，忽略上述问题强制执行演练")
        else:
            force = True  # 全部通过，无需强制勾选

        col_c1, col_c2, col_c3 = st.columns([1, 1, 1])
        with col_c1:
            if st.button("▶️ 确认执行演练", use_container_width=True, type="primary",
                         disabled=(has_fail and not force)):
                params = st.session_state.fi_pending_drill_params
                st.session_state.fi_health_check_results = None
                st.session_state.fi_pending_drill_params = None
                if params:
                    _start_drill_thread(params)
                    st.rerun()
        with col_c2:
            if st.button("✕ 取消", use_container_width=True):
                st.session_state.fi_health_check_results = None
                st.session_state.fi_pending_drill_params = None
                st.rerun()
        return  # 等待用户确认，不再显示"开始演练"按钮

    # 执行演练
    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        if st.button("🚀 开始演练", use_container_width=True, type="primary"):
            # 验证输入
            if not pod_name or not pod_name.strip():
                st.error("❌ Pod 名称不能为空")
                return

            # 验证 namespace
            is_valid, error_msg = validate_input(namespace, "命名空间")
            if not is_valid:
                st.error(f"❌ {error_msg}")
                return

            safe_pod = pod_name.strip()
            duration_str = f"{timeout}s"

            # 收集所有场景参数（供健康预检后使用）
            drill_params = {
                'namespace': namespace,
                'pod_name': safe_pod,
                'scenario': scenario,
                'timeout': timeout,
                'duration_str': duration_str,
                'check_interval': check_interval,
            }
            # 追加场景专属参数
            if scenario['type'] == 'cpu_stress':
                drill_params.update({'cpu_workers': cpu_workers, 'cpu_load': cpu_load})
            elif scenario['type'] == 'network_delay':
                drill_params.update({'net_latency': net_latency, 'net_jitter': net_jitter})
            elif scenario['type'] == 'disk_io':
                drill_params.update({'disk_path': disk_path, 'disk_fault_type': disk_fault_type, 'disk_size': disk_size})
            elif scenario['type'] == 'memory_stress':
                drill_params.update({'memory_size': memory_size, 'memory_workers': memory_workers})

            # 运行健康预检
            with st.spinner("🩺 正在进行健康预检..."):
                check_results = _run_health_check(namespace, safe_pod, scenario['type'])

            has_fail = any(r['status'] == 'fail' for r in check_results)

            if not has_fail:
                # 全部通过：直接执行演练
                _display_health_check(check_results)
                _start_drill_thread(drill_params)
                st.rerun()
            else:
                # 存在关键问题：保存结果，触发确认流程
                st.session_state.fi_health_check_results = check_results
                st.session_state.fi_pending_drill_params = drill_params
                st.rerun()


def _generate_drill_report(scenario, namespace, pod_name, start_time, end_time, drill_duration, result):
    """生成演练报告并保存到 reports 目录"""
    reports_dir = 'reports'
    os.makedirs(reports_dir, exist_ok=True)
    
    # 报告文件名
    filename = f"drill_report_{start_time.strftime('%Y%m%d_%H%M%S')}.md"
    filepath = os.path.join(reports_dir, filename)
    
    # 报告内容
    report_content = f"""# 应急演练报告

## 基本信息
- **演练场景**: {scenario['name']}
- **故障类型**: {scenario['type']}
- **命名空间**: {namespace}
- **Pod 名称**: {pod_name}
- **开始时间**: {start_time.strftime('%Y-%m-%d %H:%M:%S')}
- **结束时间**: {end_time.strftime('%Y-%m-%d %H:%M:%S')}
- **演练耗时**: {drill_duration:.2f} 秒
- **演练状态**: {'✅ 成功' if result.get('success') else '❌ 失败'}

## 演练结果
"""
    
    if result.get('success'):
        report_content += """
✅ **演练成功完成**
"""
        if result.get('recovery_time'):
            report_content += f"- Pod 恢复时间: {result['recovery_time']} 秒\n"
    else:
        report_content += f"""
❌ **演练失败**
- **失败原因**: {result.get('message', '未知错误')}
"""
    
    report_content += f"""
---
*报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""
    
    # 写入文件
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(report_content)
        return filepath
    except Exception as e:
        st.warning(f"生成报告文件失败: {e}")
        return None


def page_chain_drill():
    """多步骤故障链页面"""
    st.title("🔗 多步骤故障链")
    st.caption("按顺序执行多个故障注入、等待、告警验证步骤，模拟复杂故障场景")

    # ── 左右布局：左侧已保存故障链，右侧编辑器 ──
    left_col, right_col = st.columns([1, 2])

    with left_col:
        st.markdown("**已保存的故障链**")
        chains = db.list_drill_chains()
        if chains:
            chain_names = [c['name'] for c in chains]
            selected_chain_name = st.selectbox("选择故障链", ['（新建）'] + chain_names, key="chain_sel")
        else:
            selected_chain_name = '（新建）'
            st.info("暂无故障链，请在右侧创建")

        if selected_chain_name != '（新建）':
            chain_data = db.get_drill_chain(selected_chain_name)
            if chain_data:
                st.markdown(f"**Stage 数**: {len(_json.loads(chain_data.get('stages_json', '[]')))}")
                st.markdown(f"**描述**: {chain_data.get('description') or '（无）'}")
                if st.button("🗑️ 删除此故障链", key="chain_del"):
                    db.delete_drill_chain(selected_chain_name)
                    st.rerun()

    with right_col:
        # 初始化编辑状态
        if 'chain_stages' not in st.session_state:
            st.session_state.chain_stages = []
        if 'chain_edit_name' not in st.session_state:
            st.session_state.chain_edit_name = ''
        if 'chain_edit_desc' not in st.session_state:
            st.session_state.chain_edit_desc = ''

        # 加载已选故障链
        if selected_chain_name != '（新建）':
            chain_data = db.get_drill_chain(selected_chain_name)
            if chain_data and st.session_state.get('_chain_loaded') != selected_chain_name:
                st.session_state.chain_stages = _json.loads(chain_data.get('stages_json', '[]'))
                st.session_state.chain_edit_name = chain_data['name']
                st.session_state.chain_edit_desc = chain_data.get('description', '')
                st.session_state._chain_loaded = selected_chain_name
        elif st.session_state.get('_chain_loaded') != '（新建）':
            st.session_state.chain_stages = []
            st.session_state.chain_edit_name = ''
            st.session_state.chain_edit_desc = ''
            st.session_state._chain_loaded = '（新建）'

        name_col, desc_col = st.columns(2)
        with name_col:
            st.session_state.chain_edit_name = st.text_input(
                "故障链名称", value=st.session_state.chain_edit_name, key="chain_name_inp")
        with desc_col:
            st.session_state.chain_edit_desc = st.text_input(
                "描述（可选）", value=st.session_state.chain_edit_desc, key="chain_desc_inp")

        st.markdown("---")
        st.markdown("**Stage 列表**")

        stages = st.session_state.chain_stages
        _STAGE_TYPES = ['fault', 'wait', 'verify_alert']
        _FAULT_SCENARIOS = ['cpu_stress', 'memory_stress', 'network_delay', 'disk_io', 'pod_crash']

        for i, stage in enumerate(stages):
            with st.expander(f"Stage {i + 1}: {stage.get('type', 'wait')} — {stage.get('scenario', stage.get('wait_seconds', stage.get('alert_name', '')))}"):
                s_type = st.selectbox("类型", _STAGE_TYPES,
                                      index=_STAGE_TYPES.index(stage.get('type', 'wait')),
                                      key=f"stage_type_{i}")
                stage['type'] = s_type

                if s_type == 'fault':
                    fc1, fc2 = st.columns(2)
                    stage['scenario'] = fc1.selectbox("场景", _FAULT_SCENARIOS,
                                                      index=_FAULT_SCENARIOS.index(stage.get('scenario', 'cpu_stress')),
                                                      key=f"stage_sc_{i}")
                    stage['namespace'] = fc2.text_input("命名空间", value=stage.get('namespace', 'default'), key=f"stage_ns_{i}")
                    stage['pod_selector'] = st.text_input("Pod 名称/选择器", value=stage.get('pod_selector', ''), key=f"stage_pod_{i}")
                    stage['duration'] = st.number_input("持续秒数", min_value=5, max_value=3600, value=stage.get('duration', 60), key=f"stage_dur_{i}")
                elif s_type == 'wait':
                    stage['wait_seconds'] = st.number_input("等待秒数", min_value=1, max_value=3600, value=stage.get('wait_seconds', 10), key=f"stage_wait_{i}")
                elif s_type == 'verify_alert':
                    vc1, vc2 = st.columns(2)
                    stage['alert_name'] = vc1.text_input("告警名称", value=stage.get('alert_name', ''), key=f"stage_al_{i}")
                    stage['expected'] = vc2.selectbox("期望状态", ['firing', 'resolved'],
                                                      index=0 if stage.get('expected', 'firing') == 'firing' else 1,
                                                      key=f"stage_exp_{i}")

                btn_up, btn_down, btn_del = st.columns(3)
                with btn_up:
                    if i > 0 and st.button("↑ 上移", key=f"stage_up_{i}"):
                        stages[i], stages[i - 1] = stages[i - 1], stages[i]
                        st.rerun()
                with btn_down:
                    if i < len(stages) - 1 and st.button("↓ 下移", key=f"stage_dn_{i}"):
                        stages[i], stages[i + 1] = stages[i + 1], stages[i]
                        st.rerun()
                with btn_del:
                    if st.button("🗑️ 删除", key=f"stage_del_{i}"):
                        stages.pop(i)
                        st.rerun()

        # 添加 Stage
        add_col1, add_col2 = st.columns(2)
        with add_col1:
            if st.button("➕ 添加故障 Stage", use_container_width=True):
                stages.append({'type': 'fault', 'scenario': 'cpu_stress', 'namespace': 'default', 'pod_selector': '', 'duration': 60})
                st.rerun()
        with add_col2:
            add_type = st.selectbox("添加类型", ['wait', 'verify_alert'], key="chain_add_type", label_visibility="collapsed")
            if st.button("➕ 添加其他 Stage", use_container_width=True):
                if add_type == 'wait':
                    stages.append({'type': 'wait', 'wait_seconds': 30})
                else:
                    stages.append({'type': 'verify_alert', 'alert_name': '', 'expected': 'firing'})
                st.rerun()

        st.markdown("---")
        act_col1, act_col2 = st.columns(2)

        with act_col1:
            if st.button("💾 保存故障链", use_container_width=True):
                chain_edit_name = st.session_state.chain_edit_name.strip()
                if not chain_edit_name:
                    st.warning("请填写故障链名称")
                elif not stages:
                    st.warning("至少需要一个 Stage")
                else:
                    ok = db.save_drill_chain(chain_edit_name, st.session_state.chain_edit_desc, stages)
                    if ok:
                        st.success(f"✓ 故障链「{chain_edit_name}」已保存")
                        st.rerun()
                    else:
                        st.error("保存失败")

        with act_col2:
            if st.button("▶️ 执行故障链", use_container_width=True, type="primary"):
                if st.session_state.chaos_injector is None:
                    st.error("故障注入器未初始化，请先在设置页配置集群连接")
                elif not stages:
                    st.warning("至少需要一个 Stage")
                else:
                    chain_name_run = st.session_state.chain_edit_name.strip() or '临时故障链'
                    task_id = uuid.uuid4().hex[:8]
                    injector = st.session_state.chaos_injector
                    notify_cfg = dict(st.session_state.notify_config)
                    with _drill_tasks_lock:
                        _drill_tasks[task_id] = {
                            'status': 'running',
                            'scenario_name': f'[故障链] {chain_name_run}',
                            'current_stage': 0,
                            'total_stages': len(stages),
                            'log': [],
                        }
                    t = threading.Thread(
                        target=_run_chain_drill_background,
                        args=(task_id, chain_name_run, list(stages), injector, notify_cfg),
                        daemon=True,
                    )
                    t.start()
                    st.session_state.chain_task_id = task_id
                    st.session_state.drill_in_progress = True
                    st.rerun()

    # ── 执行状态显示 ──
    task_id = st.session_state.get('chain_task_id')
    if task_id and task_id in _drill_tasks:
        with _drill_tasks_lock:
            task = dict(_drill_tasks[task_id])
        st.markdown("---")
        st.markdown("**执行日志**")
        status = task.get('status', 'running')
        if status == 'running':
            st.info(f"🔄 执行中... Stage {task.get('current_stage', '?')}/{task.get('total_stages', '?')}")
            st.button("🔄 刷新状态", on_click=st.rerun)
        elif status == 'done':
            st.success(f"✅ 故障链执行完毕，耗时 {task.get('drill_duration', 0):.1f}s")
        elif status == 'stopped':
            st.warning("⛔ 故障链已被用户中断")
        elif status == 'error':
            st.error(f"✗ 执行出错: {task.get('error_msg', '')}")
        for line in task.get('log', []):
            st.text(line)


def page_reports():
    """演练报告页面"""
    st.title("📄 演练报告")

    # 报告列表
    reports_dir = "reports"

    if os.path.exists(reports_dir):
        reports = [f for f in os.listdir(reports_dir) if f.endswith('.md')]

        if reports:
            st.subheader("📋 报告列表")

            for report in reports:
                # 安全检查：防止路径遍历
                if '..' in report or '/' in report or '\\' in report:
                    continue

                with st.expander(report):
                    filepath = os.path.join(reports_dir, report)

                    # 验证文件路径在预期目录内
                    abs_reports_dir = os.path.abspath(reports_dir)
                    abs_filepath = os.path.abspath(filepath)
                    if not abs_filepath.startswith(abs_reports_dir):
                        st.error("无效的文件路径")
                        continue

                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            content = f.read()
                        st.markdown(content)

                        col1, col2 = st.columns(2)
                        with col1:
                            st.download_button(
                                label="📥 下载报告",
                                data=content,
                                file_name=report,
                                mime="text/markdown"
                            )
                    except Exception as e:
                        st.error(f"读取报告失败: {e}")
        else:
            st.info("暂无演练报告，请先执行演练")
    else:
        st.info("reports/ 目录不存在，请先执行演练生成报告")
    
    st.markdown("---")
    
    # 演练统计
    st.subheader("📊 演练统计")
    
    if st.session_state.drill_history:
        df = pd.DataFrame(st.session_state.drill_history)
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("总演练次数", len(df))
        
        with col2:
            if 'duration' in df.columns:
                avg_duration = df['duration'].mean()
                st.metric("平均耗时", f"{avg_duration:.2f} 秒")
            else:
                st.metric("平均耗时", "N/A")
        
        with col3:
            success_count = len(df[df['status'] == '成功'])
            success_rate = (success_count / len(df)) * 100
            st.metric("成功率", f"{success_rate:.1f}%")
        
        # 场景分布
        st.markdown("---")
        st.subheader("场景分布")
        
        if 'scenario' in df.columns:
            scenario_counts = df['scenario'].value_counts()
            st.bar_chart(scenario_counts, horizontal=True)
    else:
        st.info("暂无演练数据")

    # ── 演练历史统计与对比 ──────────────────────────────────────────────────────
    st.markdown("---")
    with st.expander("📊 演练历史统计与对比分析", expanded=False):
        history_all = db.load_drill_history()
        if not history_all:
            st.info("暂无演练历史数据")
        else:
            hdf = pd.DataFrame(history_all)
            hdf['time'] = pd.to_datetime(hdf['time'], errors='coerce')
            hdf = hdf.dropna(subset=['time'])

            # 1. 趋势图：按天统计成功/失败
            st.markdown("#### 📈 演练趋势（按天）")
            hdf['date'] = hdf['time'].dt.date
            trend = hdf.groupby(['date', 'status']).size().unstack(fill_value=0)
            if not trend.empty:
                st.bar_chart(trend)

            st.markdown("---")

            # 2. 场景对比：两个场景的平均耗时与成功率
            st.markdown("#### 🆚 场景对比")
            scenarios_available = sorted(hdf['scenario'].unique().tolist())
            if len(scenarios_available) >= 2:
                cmp_col1, cmp_col2 = st.columns(2)
                with cmp_col1:
                    sc_a = st.selectbox("场景 A", scenarios_available, key="cmp_sc_a")
                with cmp_col2:
                    remaining = [s for s in scenarios_available if s != sc_a]
                    sc_b = st.selectbox("场景 B", remaining if remaining else scenarios_available, key="cmp_sc_b")

                def _scenario_stats(df, sc):
                    sub = df[df['scenario'] == sc]
                    total = len(sub)
                    success = len(sub[sub['status'] == '成功'])
                    avg_dur = sub['duration'].mean() if 'duration' in sub.columns and total > 0 else 0
                    return total, success, round(avg_dur, 2)

                ta, sa, da = _scenario_stats(hdf, sc_a)
                tb, sb, db_val = _scenario_stats(hdf, sc_b)

                cmp_data = pd.DataFrame({
                    '指标': ['演练次数', '成功次数', '成功率 (%)', '平均耗时 (s)'],
                    sc_a: [ta, sa, round(sa / ta * 100, 1) if ta else 0, da],
                    sc_b: [tb, sb, round(sb / tb * 100, 1) if tb else 0, db_val],
                })
                st.dataframe(cmp_data, use_container_width=True, hide_index=True)
            else:
                st.info("需要至少 2 种场景才能进行对比")

            st.markdown("---")

            # 3. 单次记录对比：选 2 条并排展示
            st.markdown("#### 🔍 单次记录详情对比")
            record_labels = [f"#{r['id']} {r['time'].strftime('%m-%d %H:%M') if hasattr(r['time'], 'strftime') else str(r['time'])} | {r['scenario']} | {r['status']}" for _, r in hdf.iterrows()]
            selected_records = st.multiselect("选择 2 条记录进行对比", record_labels, max_selections=2, key="cmp_records")
            if len(selected_records) == 2:
                def _get_row(label):
                    idx = record_labels.index(label)
                    return hdf.iloc[idx]
                r1 = _get_row(selected_records[0])
                r2 = _get_row(selected_records[1])
                rc1, rc2 = st.columns(2)
                for col, row in [(rc1, r1), (rc2, r2)]:
                    with col:
                        st.markdown(f"**场景**: {row.get('scenario', '-')}")
                        st.markdown(f"**状态**: {row.get('status', '-')}")
                        st.markdown(f"**耗时**: {row.get('duration', '-')} 秒")
                        st.markdown(f"**时间**: {row.get('time', '-')}")
                        st.markdown(f"**消息**: {row.get('message', '（无）')}")


def page_settings():
    """设置页面 - 含配置档案管理"""
    st.title("⚙️ 设置")

    tab_cluster, tab_monitor, tab_notify, tab_schedule = st.tabs(["🔗 集群连接", "📊 监控", "🔔 通知", "🗓️ 演练计划"])

    # ── 集群连接 ──────────────────────────────────────────────────────────────
    with tab_cluster:
        k8s_profiles = db.list_k8s_profiles()
        profile_names = [p['name'] for p in k8s_profiles]

        if profile_names:
            default_idx = next((i for i, p in enumerate(k8s_profiles) if p.get('is_default')), 0)
            selected_profile = st.selectbox("选择配置档案", profile_names, index=default_idx)
            # 切换档案时自动加载
            if st.session_state.get('_k8s_sel') != selected_profile:
                st.session_state._k8s_sel = selected_profile
                loaded = db.get_k8s_profile(selected_profile)
                if loaded:
                    st.session_state.cluster_config = {**_DEFAULT_CLUSTER, **loaded}
                    st.session_state.chaos_injector = None
        else:
            selected_profile = ""
            st.info("尚无已保存的配置档案，请填写下方配置并保存")

        st.markdown("---")

        # 连接状态展示
        if st.session_state.cluster_config.get('connected'):
            ci = st.session_state.cluster_config.get('cluster_info', {})
            c1, c2, c3 = st.columns(3)
            c1.metric("集群名称", ci.get('cluster_name', 'N/A'))
            c2.metric("K8s 版本", ci.get('kubernetes_version', 'N/A'))
            c3.metric("节点数量", ci.get('node_count', 'N/A'))
            inj_status = "就绪 ✓" if st.session_state.chaos_injector else "未初始化"
            st.success(f"✓ 集群已连接  |  故障注入器: {inj_status}")
        else:
            st.warning("⚠ 集群未连接")

        st.markdown("---")

        # 连接方式
        connection_type = st.radio(
            "连接方式",
            ["kubeconfig", "Token"],
            index=0 if st.session_state.cluster_config.get('connection_type', 'kubeconfig') == 'kubeconfig' else 1,
            horizontal=True,
        )
        st.session_state.cluster_config['connection_type'] = connection_type

        if connection_type == "kubeconfig":
            kubeconfig_path = st.text_input(
                "Kubeconfig 路径",
                value=st.session_state.cluster_config.get('kubeconfig_path', os.path.expanduser('~/.kube/config')),
            )
            st.session_state.cluster_config['kubeconfig_path'] = kubeconfig_path
            ep = os.path.expanduser(kubeconfig_path) if kubeconfig_path else ''
            if ep:
                st.caption(("✓ 文件存在: " if os.path.exists(ep) else "✗ 文件不存在: ") + ep)
        else:
            c1, c2 = st.columns([3, 2])
            with c1:
                api_server = st.text_input(
                    "API Server 地址",
                    value=st.session_state.cluster_config.get('api_server', ''),
                    placeholder="https://192.168.1.100:6443",
                )
                st.session_state.cluster_config['api_server'] = api_server
            with c2:
                ca_cert = st.text_area(
                    "CA 证书 (可选)",
                    value=st.session_state.cluster_config.get('ca_cert', ''),
                    height=100,
                )
                st.session_state.cluster_config['ca_cert'] = ca_cert
            token = st.text_area(
                "Service Account Token",
                value=st.session_state.cluster_config.get('token', ''),
                height=120,
            )
            st.session_state.cluster_config['token'] = token

        st.markdown("---")

        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("🔌 测试并连接", use_container_width=True, type="primary"):
                _do_k8s_connect()
        with col_b:
            if st.button("🔄 重置配置", use_container_width=True):
                st.session_state.cluster_config = {**_DEFAULT_CLUSTER}
                st.session_state.chaos_injector = None
                st.session_state._k8s_sel = None
                st.rerun()

        st.markdown("---")

        st.markdown('<p class="section-title">档案管理</p>', unsafe_allow_html=True)
        profile_name_input = st.text_input(
            "档案名称",
            value=selected_profile or "新配置",
            placeholder="为此配置命名",
            key="k8s_profile_name_input",
        )
        col_s, col_d, col_def = st.columns(3)
        with col_s:
            if st.button("💾 保存档案", use_container_width=True):
                _save_k8s_profile_action(profile_name_input)
        with col_d:
            if selected_profile and st.button("🗑 删除档案", use_container_width=True):
                db.delete_k8s_profile(selected_profile)
                st.session_state.cluster_config = {**_DEFAULT_CLUSTER}
                st.session_state.chaos_injector = None
                st.session_state._k8s_sel = None
                st.rerun()
        with col_def:
            if selected_profile and st.button("⭐ 设为默认", use_container_width=True):
                db.set_default_k8s_profile(selected_profile)
                st.success(f"✓ 「{selected_profile}」已设为默认")
                st.rerun()

        st.markdown("---")

        # 集群资源浏览（仅连接后显示）
        if st.session_state.cluster_config.get('connected') and st.session_state.chaos_injector:
            st.subheader("📋 集群资源浏览")
            try:
                injector = st.session_state.chaos_injector
                namespaces = injector.list_namespaces()
                ns = st.selectbox("选择命名空间", ["全部"] + namespaces)
                if ns != "全部":
                    pods = injector.list_pods(ns)
                    deployments = injector.list_deployments(ns)
                    col_res1, col_res2 = st.columns(2)
                    with col_res1:
                        st.markdown(f"**Pods** ({len(pods)})")
                        if pods:
                            for p in pods:
                                status_icon = "🟢" if p.get('status') == 'Running' else "🔴"
                                st.caption(f"{status_icon} {p['name']} | {p.get('status', 'N/A')}")
                        else:
                            st.caption("（无 Pod）")
                    with col_res2:
                        st.markdown(f"**Deployments** ({len(deployments)})")
                        if deployments:
                            for d in deployments:
                                avail = d.get('available_replicas', 0)
                                total = d.get('replicas', 0)
                                st.caption(f"📦 {d['name']} | {avail}/{total}")
                        else:
                            st.caption("（无 Deployment）")
                else:
                    st.info("请选择具体命名空间查看资源")
            except Exception as e:
                st.error(f"获取资源失败: {e}")

    # ── 监控 ──────────────────────────────────────────────────────────────────
    with tab_monitor:
        mon_profiles = db.list_monitor_profiles()
        mon_names = [p['name'] for p in mon_profiles]

        if mon_names:
            default_mon_idx = next((i for i, p in enumerate(mon_profiles) if p.get('is_default')), 0)
            selected_mon = st.selectbox("选择监控档案", mon_names, index=default_mon_idx)
            if st.session_state.get('_mon_sel') != selected_mon:
                st.session_state._mon_sel = selected_mon
                lm = db.get_monitor_profile(selected_mon)
                if lm:
                    st.session_state.monitor_config = {**_DEFAULT_MONITOR, **lm}
                    st.session_state.monitor_checker = None
        else:
            selected_mon = ""
            st.info("尚无已保存的监控档案，请填写下方配置并保存")

        st.markdown("---")

        col1, col2 = st.columns(2)
        with col1:
            prometheus_url = st.text_input(
                "Prometheus URL",
                value=st.session_state.monitor_config.get('prometheus_url', 'http://localhost:9090'),
            )
        with col2:
            username = st.text_input(
                "用户名",
                value=st.session_state.monitor_config.get('username', ''),
                placeholder="可选",
            )
            password = st.text_input("密码", type="password", placeholder="可选（不会保存）")

        if st.session_state.monitor_checker is not None:
            st.success("✓ 监控已连接")
        else:
            st.warning("⚠ 监控未连接")

        st.markdown("---")

        col_ma, col_mb = st.columns(2)
        with col_ma:
            if st.button("🔌 连接监控", use_container_width=True, type="primary"):
                try:
                    st.session_state.monitor_checker = MonitorChecker(prometheus_url, username, password or None)
                    st.session_state.monitor_config['prometheus_url'] = prometheus_url
                    st.session_state.monitor_config['username'] = username
                    st.success("✓ 监控已连接")
                    st.rerun()
                except Exception as e:
                    st.error(f"✗ 连接失败: {e}")
        with col_mb:
            if st.button("🔄 断开监控", use_container_width=True):
                st.session_state.monitor_checker = None
                st.rerun()

        st.markdown("---")

        st.markdown('<p class="section-title">档案管理</p>', unsafe_allow_html=True)
        mon_name_input = st.text_input(
            "档案名称",
            value=selected_mon or "默认监控",
            key="mon_profile_name_input",
        )
        col_ms, col_md, col_mdef = st.columns(3)
        with col_ms:
            if st.button("💾 保存监控档案", use_container_width=True):
                n = mon_name_input.strip()
                if n:
                    ok = db.save_monitor_profile(
                        n,
                        {'prometheus_url': prometheus_url, 'username': username, 'password': ''},
                        set_default=True,
                    )
                    if ok:
                        st.success(f"✓ 已保存「{n}」")
                        st.rerun()
                else:
                    st.error("请输入档案名称")
        with col_md:
            if selected_mon and st.button("🗑 删除监控档案", use_container_width=True):
                db.delete_monitor_profile(selected_mon)
                st.session_state.monitor_config = {**_DEFAULT_MONITOR}
                st.session_state.monitor_checker = None
                st.session_state._mon_sel = None
                st.rerun()
        with col_mdef:
            if selected_mon and st.button("⭐ 设为默认", use_container_width=True, key="mon_set_default"):
                db.set_default_monitor_profile(selected_mon)
                st.success(f"✓ 「{selected_mon}」已设为默认")
                st.rerun()

        if st.session_state.monitor_checker is not None:
            st.markdown("---")
            st.subheader("🔔 告警查询")

            col1, col2 = st.columns(2)
            with col1:
                alert_name = st.text_input("告警名称", placeholder="例如: PodCrashLooping")
            with col2:
                st.number_input("等待超时(秒)", min_value=10, max_value=600, value=60)

            if st.button("🔍 查询告警", use_container_width=True):
                with st.spinner("正在查询告警..."):
                    alert = st.session_state.monitor_checker.prometheus.query_alert_by_name(alert_name)
                    if alert:
                        st.success(f"✓ 找到告警: {alert_name}")
                        labels = alert.get('labels', {})
                        with st.expander("📋 告警详情", expanded=True):
                            st.write(f"**告警名称**: {labels.get('alertname', 'N/A')}")
                            st.write(f"**严重级别**: {labels.get('severity', 'N/A')}")
                            st.write(f"**状态**: {alert.get('state', 'N/A')}")
                            st.write(f"**描述**: {alert.get('annotations', {}).get('summary', 'N/A')}")
                            st.write(f"**标签**: {labels}")
                    else:
                        st.info(f"未找到告警: {alert_name}")

            st.markdown("---")

            col1, col2 = st.columns([2, 1])
            with col1:
                if st.button("📡 查询所有告警", use_container_width=True):
                    with st.spinner("正在查询..."):
                        alerts = st.session_state.monitor_checker.prometheus.query_alerts()
                        if alerts:
                            st.success(f"✓ 查询到 {len(alerts)} 个告警")
                            for i, alert in enumerate(alerts, 1):
                                labels = alert.get('labels', {})
                                with st.expander(f"{i}. {labels.get('alertname', 'N/A')} - {alert.get('state', 'N/A').upper()}"):
                                    st.write(f"**严重级别**: {labels.get('severity', 'N/A')}")
                                    st.write(f"**状态**: {alert.get('state', 'N/A')}")
                                    st.write(f"**描述**: {alert.get('annotations', {}).get('summary', 'N/A')}")
                                    st.write(f"**标签**: {labels}")
                        else:
                            st.info("当前没有活跃告警")
            with col2:
                if st.button("🔄 刷新告警", use_container_width=True):
                    st.rerun()

    # ── 通知 ──────────────────────────────────────────────────────────────────
    with tab_notify:
        st.caption("配置 Webhook 通知，当演练完成或失败时自动推送消息")
        ncfg = st.session_state.notify_config
        enable_notification = st.checkbox("启用 Webhook 通知", value=ncfg.get('enabled', False))
        webhook_url = st.text_input(
            "Webhook URL",
            value=ncfg.get('webhook_url', ''),
            placeholder="例如: https://hooks.slack.com/... 或企业微信机器人地址",
        )
        notify_events = st.multiselect(
            "触发通知的事件",
            ["演练开始", "演练完成", "演练失败"],
            default=ncfg.get('events', ['演练完成', '演练失败']),
        )
        st.markdown("---")
        col_nsave, col_ntest = st.columns(2)
        with col_nsave:
            if st.button("💾 保存通知配置", use_container_width=True):
                st.session_state.notify_config = {
                    'enabled': enable_notification,
                    'webhook_url': webhook_url,
                    'events': notify_events,
                }
                st.success("✓ 通知配置已保存")
        with col_ntest:
            if st.button("🧪 发送测试通知", use_container_width=True):
                if not webhook_url.strip():
                    st.warning("请先填写 Webhook URL")
                else:
                    import requests as _req
                    try:
                        _req.post(webhook_url.strip(), json={
                            'event': '测试通知',
                            'platform': '应急演练智能平台',
                            'message': '这是来自应急演练智能平台的测试通知',
                        }, timeout=5)
                        st.success("✓ 测试通知已发送，请检查目标系统是否收到")
                    except Exception as e:
                        st.error(f"✗ 发送失败: {e}")
        st.caption("💡 Payload 格式：JSON，包含 event, platform, time, scenario, status, duration 等字段")

    # ── 演练计划 / 定时调度 ──────────────────────────────────────────────────────
    with tab_schedule:
        if not _SCHEDULER_AVAILABLE:
            st.error("❌ APScheduler 未安装，请运行 `pip install apscheduler` 后重启应用")
        else:
            st.caption("配置定时演练计划，按 Cron 表达式自动触发（需保持应用运行）")
            st.info("💡 Cron 格式：`分 时 日 月 周`，例如 `0 2 * * *` = 每天凌晨 2 点，`*/30 * * * *` = 每 30 分钟")

            # ── 现有计划列表 ──
            schedules = db.list_drill_schedules()
            if schedules:
                st.markdown("**已配置的演练计划**")
                for s in schedules:
                    with st.expander(f"{'✅' if s['enabled'] else '⏸️'} {s['name']}  |  `{s['cron_expr']}`  |  {s['scenario']}"):
                        sc1, sc2, sc3 = st.columns(3)
                        sc1.write(f"**命名空间**: {s['namespace']}")
                        sc2.write(f"**Pod 选择器**: {s['pod_selector'] or '（空）'}")
                        sc3.write(f"**下次执行**: {s.get('next_run') or '待计算'}")
                        sc4, sc5, sc6 = st.columns(3)
                        sc4.write(f"**上次执行**: {s.get('last_run') or '从未'}")
                        btn_cols = st.columns(3)
                        with btn_cols[0]:
                            toggle_label = "⏸️ 禁用" if s['enabled'] else "▶️ 启用"
                            if st.button(toggle_label, key=f"sched_tog_{s['name']}"):
                                db.save_drill_schedule(s['name'], {**s, 'enabled': 0 if s['enabled'] else 1})
                                _reload_schedules_from_db()
                                st.rerun()
                        with btn_cols[1]:
                            if st.button("🗑️ 删除", key=f"sched_del_{s['name']}"):
                                db.delete_drill_schedule(s['name'])
                                _reload_schedules_from_db()
                                st.rerun()
            else:
                st.info("暂无演练计划，请在下方添加")

            st.markdown("---")
            st.markdown("**➕ 添加 / 更新演练计划**")
            _SCENARIO_OPTIONS = ['cpu_stress', 'memory_stress', 'network_delay', 'disk_io', 'pod_crash']
            sn_col1, sn_col2 = st.columns(2)
            with sn_col1:
                sched_name = st.text_input("计划名称", placeholder="例如: 每日CPU压测", key="sched_name")
                sched_cron = st.text_input("Cron 表达式", value="0 2 * * *", key="sched_cron",
                                           help="分 时 日 月 周")
                sched_scenario = st.selectbox("演练场景", _SCENARIO_OPTIONS, key="sched_scenario")
            with sn_col2:
                sched_ns = st.text_input("命名空间", value="default", key="sched_ns")
                sched_pod = st.text_input("Pod 选择器（名称或部分名称）", key="sched_pod")
                sched_duration = st.number_input("持续时间（秒）", min_value=10, max_value=3600, value=60, key="sched_dur")
            if st.button("💾 保存计划", use_container_width=True, key="sched_save"):
                if not sched_name.strip():
                    st.warning("请填写计划名称")
                elif not sched_cron.strip():
                    st.warning("请填写 Cron 表达式")
                else:
                    ok = db.save_drill_schedule(sched_name.strip(), {
                        'enabled': 1,
                        'cron_expr': sched_cron.strip(),
                        'scenario': sched_scenario,
                        'namespace': sched_ns.strip(),
                        'pod_selector': sched_pod.strip(),
                        'params_json': _json.dumps({'duration': sched_duration}),
                    })
                    if ok:
                        _reload_schedules_from_db()
                        st.success(f"✓ 计划「{sched_name}」已保存并注册")
                        st.rerun()
                    else:
                        st.error("保存失败，请检查计划名称是否重复")


def page_grafana():
    """监控面板页面 - 原生 Prometheus 趋势图"""
    import time as _time
    import streamlit.components.v1 as components

    st.title("📊 监控面板")

    prom = st.session_state.monitor_checker
    if prom is None:
        st.warning("⚠ 监控未连接，请先在「⚙️ 设置 → 监控」中配置并连接 Prometheus")
        if st.button("前往设置"):
            st.session_state._nav_target = "⚙️ 设置"
            st.rerun()
        return

    # ── 工具栏 ──────────────────────────────────────────────────────────
    c_range, c_ns, c_pod, c_refresh = st.columns([2, 2, 2, 1])
    with c_range:
        time_range = st.selectbox(
            "时间范围",
            ["最近 15 分钟", "最近 1 小时", "最近 6 小时", "最近 24 小时"],
            index=1,
            key="mon_time_range",
            label_visibility="collapsed",
        )
    with c_ns:
        ns_filter = st.text_input("命名空间过滤", value="", placeholder="命名空间（留空=全部）", key="mon_ns", label_visibility="collapsed")
    with c_pod:
        pod_filter = st.text_input("Pod 过滤", value="", placeholder="Pod 名称（支持正则）", key="mon_pod", label_visibility="collapsed")
    with c_refresh:
        do_refresh = st.button("🔄 刷新", use_container_width=True, key="mon_refresh")

    # ── 计算时间范围 ─────────────────────────────────────────────────────
    now = _time.time()
    range_map = {
        "最近 15 分钟": (now - 900,  "15s"),
        "最近 1 小时":  (now - 3600, "30s"),
        "最近 6 小时":  (now - 21600,"120s"),
        "最近 24 小时": (now - 86400,"300s"),
    }
    start_ts, step = range_map[time_range]

    # ── 辅助：Prometheus 范围查询 → DataFrame ────────────────────────────
    def _query_df(query: str, label_key: str = None, value_scale: float = 1.0):
        """执行范围查询，返回以时间为索引的 DataFrame"""
        series_list = prom.prometheus.query_range(query, start_ts, now, step)
        if not series_list:
            return pd.DataFrame()
        dfs = []
        for s in series_list:
            m = s.get('metric', {})
            vals = s.get('values', [])
            if not vals:
                continue
            if label_key and m.get(label_key):
                col = m[label_key]
            elif m.get('pod'):
                col = m['pod']
            elif m.get('__name__'):
                col = m['__name__']
            else:
                col = str(m)[:40]
            timestamps = [datetime.fromtimestamp(float(ts)) for ts, _ in vals]
            values = [float(v) * value_scale for _, v in vals]
            dfs.append(pd.DataFrame({col: values}, index=timestamps))
        if not dfs:
            return pd.DataFrame()
        result = dfs[0]
        for df in dfs[1:]:
            result = result.join(df, how='outer')
        return result

    # ── Prometheus 直连辅助（绕过封装，拿到原始错误）────────────────────
    import requests as _req
    _prom_url  = prom.prometheus.url
    _prom_auth = prom.prometheus.auth

    def _instant(q):
        """即时查询 /api/v1/query → (result_list, error_str)"""
        try:
            r = _req.get(f"{_prom_url}/api/v1/query",
                         params={'query': q}, auth=_prom_auth, timeout=8)
            d = r.json()
            if d.get('status') == 'success':
                return d['data']['result'], None
            return [], d.get('error', f'status={d.get("status")}')
        except Exception as exc:
            return [], str(exc)

    def _range_q(q):
        """范围查询 /api/v1/query_range → (result_list, error_str)"""
        try:
            r = _req.get(f"{_prom_url}/api/v1/query_range",
                         params={'query': q, 'start': start_ts,
                                 'end': now, 'step': step},
                         auth=_prom_auth, timeout=15)
            d = r.json()
            if d.get('status') == 'success':
                return d['data']['result'], None
            return [], d.get('error', f'status={d.get("status")}')
        except Exception as exc:
            return [], str(exc)

    # ── 自动检测 cAdvisor label 格式 ────────────────────────────────────
    # 第一步：检测 namespace + pod（不强求 container，因为有些 scrape 配置没有该标签）
    _pod_chk, _ = _instant(
        'count(container_cpu_usage_seconds_total{namespace!="",pod!=""})'
    )
    if _pod_chk and int(float(_pod_chk[0]['value'][1])) > 0:
        _ns_lbl, _pod_lbl = 'namespace', 'pod'
        # 单独检测 container 标签是否存在
        _cont_chk, _ = _instant(
            'count(container_cpu_usage_seconds_total{namespace!="",pod!="",container!=""})'
        )
        _cont_lbl = 'container' if (_cont_chk and int(float(_cont_chk[0]['value'][1])) > 0) else None
        _label_fmt = 'standard'
    else:
        # 备用：cAdvisor 直接暴露时的 container_label_* 格式
        _alt_chk, _ = _instant(
            'count(container_cpu_usage_seconds_total'
            '{container_label_io_kubernetes_pod_namespace!=""})'
        )
        if _alt_chk and int(float(_alt_chk[0]['value'][1])) > 0:
            _ns_lbl   = 'container_label_io_kubernetes_pod_namespace'
            _pod_lbl  = 'container_label_io_kubernetes_pod_name'
            _cont_lbl = 'container_label_io_kubernetes_container_name'
            _label_fmt = 'container_label'
        else:
            _ns_lbl, _pod_lbl, _cont_lbl = 'namespace', 'pod', None
            _label_fmt = 'unknown'

    # ── 构建 PromQL 过滤器 ───────────────────────────────────────────────
    ns_selector  = f'{_ns_lbl}="{ns_filter}"' if ns_filter else f'{_ns_lbl}!=""'
    pod_selector = f'{_pod_lbl}=~"{pod_filter}.*"' if pod_filter else f'{_pod_lbl}!=""'
    # 仅当 container 标签确实存在时才加 container 过滤，否则会过滤掉所有数据
    if _cont_lbl:
        container_selector = f'{_cont_lbl}!="",{_cont_lbl}!="POD",{ns_selector},{pod_selector}'
    else:
        container_selector = f'{ns_selector},{pod_selector}'

    st.markdown("---")

    # ── 第一行：告警数 + Pod 重启 ────────────────────────────────────────
    row1_left, row1_right = st.columns(2)

    with row1_left:
        st.subheader("🔔 活跃告警数")
        df_alerts = _query_df('sum(ALERTS{alertstate="firing"}) or vector(0)', label_key="__name__")
        if not df_alerts.empty:
            df_alerts.columns = ["告警数"]
            st.line_chart(df_alerts, use_container_width=True)
        else:
            st.info("暂无数据（Prometheus 未返回该指标）")

    with row1_right:
        st.subheader("🔁 Pod 重启次数（增量）")
        df_restart = _query_df(
            f'sum by (pod) (increase(kube_pod_container_status_restarts_total{{{ns_selector},{pod_selector}}}[1m]))',
        )
        if not df_restart.empty:
            st.line_chart(df_restart, use_container_width=True)
        else:
            st.info("暂无数据（需要 kube-state-metrics）")

    # ── 第二行：CPU + 内存 ───────────────────────────────────────────────
    row2_left, row2_right = st.columns(2)

    with row2_left:
        st.subheader("⚡ CPU 使用率（%）")
        df_cpu = _query_df(
            f'sum by ({_pod_lbl}) (rate(container_cpu_usage_seconds_total{{{container_selector}}}[2m]))',
            label_key=_pod_lbl,
            value_scale=100,
        )
        if not df_cpu.empty:
            st.line_chart(df_cpu, use_container_width=True)
        else:
            st.info("暂无数据（需要 cAdvisor / kubelet metrics）")

    with row2_right:
        st.subheader("🧠 内存使用量（MB）")
        df_mem = _query_df(
            f'sum by ({_pod_lbl}) (container_memory_working_set_bytes{{{container_selector}}})',
            label_key=_pod_lbl,
            value_scale=1 / (1024 * 1024),
        )
        if not df_mem.empty:
            st.line_chart(df_mem, use_container_width=True)
        else:
            st.info("暂无数据（需要 cAdvisor / kubelet metrics）")

    # ── 第三行：网络 + EDAP 自定义指标 ──────────────────────────────────
    row3_left, row3_right = st.columns(2)

    with row3_left:
        st.subheader("🌐 网络接收流量（KB/s）")
        df_net = _query_df(
            f'sum by ({_pod_lbl}) (rate(container_network_receive_bytes_total{{{ns_selector},{pod_selector}}}[2m]))',
            label_key=_pod_lbl,
            value_scale=1 / 1024,
        )
        if not df_net.empty:
            st.line_chart(df_net, use_container_width=True)
        else:
            _net_exist, _ = _instant('count(container_network_receive_bytes_total)')
            if not _net_exist or int(float(_net_exist[0]['value'][1])) == 0:
                st.warning("⚠ container_network_receive_bytes_total 不存在于 Prometheus\n\n"
                           "该指标需要 cAdvisor 网络采集已启用。部分 k8s 发行版默认不暴露网络指标，"
                           "可在 Prometheus 控制台搜索 `container_network` 确认。")
            else:
                cnt_net = int(float(_net_exist[0]['value'][1]))
                _net_sample, _ = _instant('topk(1, container_network_receive_bytes_total)')
                sample_lbl = _net_sample[0]['metric'] if _net_sample else {}
                missing = [k for k in (_ns_lbl, _pod_lbl) if k not in sample_lbl]
                if missing:
                    st.warning(f"⚠ 指标存在（{cnt_net} 条）但缺少 label: `{missing}`\n\n"
                               f"实际 labels: `{list(sample_lbl.keys())}`")
                else:
                    st.info(f"指标存在（{cnt_net} 条），labels 正常，请检查命名空间/Pod 过滤条件")

    with row3_right:
        st.subheader("🎯 EDAP 演练恢复时间（秒）")
        df_edap = _query_df('edap_recovery_time_seconds', label_key='scenario')
        if not df_edap.empty:
            st.line_chart(df_edap, use_container_width=True)
        else:
            st.info("暂无演练指标\n\n需要同时满足两个条件才会有数据：\n"
                    "1. 在「⚙️ 设置 → Grafana / Pushgateway」中填写 Pushgateway 地址并启用\n"
                    "2. 完成至少一次故障注入演练（演练结束后自动推送指标）")

    # ── 底部：当前活跃告警快览 ───────────────────────────────────────────
    st.markdown("---")

    # ── 诊断区：无数据时自动展开，复用上方 _instant/_range_q ─────────────────────
    _all_empty = df_cpu.empty and df_mem.empty and df_net.empty
    with st.expander("🔍 诊断（图表无数据时自动展开）", expanded=_all_empty):

        # ── 检测结果摘要 ─────────────────────────────────────────────────
        st.markdown("##### label 格式自动检测结果")
        fmt_map = {
            'standard':       ('✅ 标准格式',
                               'kubelet /metrics/cadvisor + k8s relabeling',
                               f'`{_ns_lbl}` / `{_pod_lbl}`'
                               + (f' / `{_cont_lbl}`' if _cont_lbl else ' （无 container 标签）')),
            'container_label': ('✅ cAdvisor 直接抓取格式',
                                'Prometheus 直接抓 cAdvisor，无 k8s relabeling',
                                f'`{_ns_lbl}` / `{_pod_lbl}` / `{_cont_lbl}`'),
            'unknown':         ('❌ 未检测到已知格式',
                                '以上格式均无匹配数据', '无法自动适配'),
        }
        icon, desc, lbl_names = fmt_map[_label_fmt]
        st.info(f"{icon}  \n**格式**: {desc}  \n**当前使用的 label**: {lbl_names}")

        if _label_fmt == 'unknown':
            st.error("无法确定 label 格式，图表将无数据。请参考下方步骤排查。")

        st.markdown("##### 步骤 1 — cAdvisor 指标是否存在")
        res1, err1 = _instant('count(container_cpu_usage_seconds_total)')
        if err1:
            st.error(f"❌ 查询报错: `{err1}`")
        elif res1:
            st.success(f"✓ container_cpu_usage_seconds_total 存在，共 **{int(float(res1[0]['value'][1]))}** 条时序")
        else:
            st.error("❌ 指标不存在 → Prometheus 未采集 cAdvisor")

        st.markdown("##### 步骤 2 — 容器级 label 样本（排除根 cgroup `id=/`）")
        res2, _ = _instant('topk(1, container_cpu_usage_seconds_total{id!="/"})')
        if res2:
            st.json(res2[0]['metric'])
        else:
            st.warning("无容器级样本，只有根 cgroup 数据")

        st.markdown("##### 步骤 3 — 无过滤范围查询")
        res3, err3 = _range_q('sum(rate(container_cpu_usage_seconds_total[2m]))')
        if err3:
            st.error(f"❌ 范围查询报错: `{err3}`")
        elif res3:
            v = round(float(res3[0].get('values', [[0, '0']])[-1][1]), 4)
            st.success(f"✓ 正常，集群 CPU 总使用率 ≈ **{v} 核**")
        else:
            st.warning("⚠ 无过滤也无数据 — 时间范围内可能无数据点")

        st.markdown("##### 步骤 4 — 当前过滤器查询（与图表一致）")
        _cpu_q = f'sum by ({_pod_lbl}) (rate(container_cpu_usage_seconds_total{{{container_selector}}}[2m]))'
        res4, err4 = _range_q(_cpu_q)
        if err4:
            st.error(f"❌ 查询语法/执行错误: `{err4}`")
        elif res4:
            st.success(f"✓ 有 {len(res4)} 条时序，图表应显示 — 请点击「🔄 刷新」")
        else:
            st.warning("⚠ 带过滤器查询无数据，步骤 3 有数据 → 过滤器不匹配")

        st.markdown("##### 当前实际查询语句")
        st.code(_cpu_q, language="text")

    st.subheader("📋 当前活跃告警")
    try:
        alerts = prom.prometheus.query_alerts()
        firing = [a for a in alerts if a.get('state') == 'firing']
        if firing:
            for a in firing:
                labels = a.get('labels', {})
                severity = labels.get('severity', 'unknown')
                color = {"critical": "🔴", "warning": "🟡"}.get(severity, "🔵")
                st.markdown(
                    f"{color} **{labels.get('alertname', 'N/A')}** "
                    f"| 级别: `{severity}` "
                    f"| {a.get('annotations', {}).get('summary', '')}"
                )
        else:
            st.success("✓ 当前无触发告警")
    except Exception as e:
        st.error(f"查询告警失败: {e}")

    # ── 可折叠：Grafana 管理（高级用法）────────────────────────────────
    with st.expander("🔧 Grafana 高级配置（可选）", expanded=False):
        st.caption("如果你有 Grafana，可以在这里连接并自动创建演练仪表板")
        cfg = st.session_state.grafana_config
        gi  = st.session_state.grafana_integration

        if gi and gi.is_connected():
            st.success(f"✓ 已连接 Grafana: {cfg.get('grafana_url')}")
            gc1, gc2, gc3 = st.columns(3)
            with gc1:
                if st.button("🆕 创建总览仪表板", key="gf_ov2"):
                    with st.spinner("创建中..."):
                        try:
                            r = gi.dashboard_manager.create_drill_overview_dashboard()
                            if r:
                                st.success(f"✓ {r['title']}")
                                st.markdown(f"[打开]({r['url']})")
                            else:
                                st.error("✗ 创建失败，请确认 Prometheus 数据源已配置")
                        except Exception as e:
                            st.error(str(e))
            with gc2:
                st.markdown(f"[🔗 打开 Grafana]({cfg.get('grafana_url', 'http://localhost:3000')})")
            with gc3:
                if st.button("🔌 断开 Grafana", key="gf_dis2"):
                    st.session_state.grafana_integration = None
                    st.rerun()
        else:
            g_url  = st.text_input("Grafana URL",  value=cfg.get('grafana_url', 'http://localhost:3000'), key="gf2_url")
            g_user = st.text_input("用户名", value=cfg.get('grafana_username', 'admin'), key="gf2_user")
            g_pass = st.text_input("密码",   type="password", placeholder="不保存明文", key="gf2_pass")
            g_ds   = st.text_input("Prometheus 数据源名称", value=cfg.get('prometheus_datasource', 'Prometheus'), key="gf2_ds")
            if st.button("🔌 连接 Grafana", key="gf2_conn"):
                try:
                    new_gi = GrafanaIntegration(
                        grafana_url=g_url,
                        grafana_username=g_user,
                        grafana_password=g_pass,
                        prometheus_datasource=g_ds,
                    )
                    if new_gi.is_connected():
                        st.session_state.grafana_integration = new_gi
                        st.session_state.grafana_config.update({
                            'grafana_url': g_url, 'grafana_username': g_user,
                            'prometheus_datasource': g_ds, 'enabled': True,
                        })
                        st.success("✓ 连接成功")
                        st.rerun()
                    else:
                        st.error("✗ 连接失败")
                except Exception as e:
                    st.error(str(e))


def main():
    """主函数"""
    # 侧边栏导航
    with st.sidebar:
        st.markdown(
            '<div style="padding:8px 0 12px 0;">'
            '<div style="font-size:1.4rem;font-weight:800;color:#FFFFFF;letter-spacing:-0.5px;line-height:1.3;">应急演练智能平台</div>'
            '<div style="font-size:0.7rem;color:#64748B;letter-spacing:.08em;text-transform:uppercase;margin-top:4px;">Emergency Drill Platform</div>'
            '</div>',
            unsafe_allow_html=True,
        )
        st.markdown("---")
        
        # 系统状态
        st.subheader("系统状态")
        injector_ok = st.session_state.chaos_injector is not None
        monitor_ok  = st.session_state.monitor_checker is not None
        st.markdown(
            f"""
<div style="display:flex;flex-direction:column;gap:6px;margin:4px 0 8px 0;">
  <div style="display:flex;align-items:center;gap:8px;
              background:{'#0D3320' if injector_ok else '#3A0E0E'};
              border:1px solid {'#16A34A' if injector_ok else '#DC2626'};
              border-radius:8px;padding:8px 12px;">
    <span style="font-size:1rem;">{'✅' if injector_ok else '❌'}</span>
    <span style="color:{'#4ADE80' if injector_ok else '#FCA5A5'};
                 font-size:0.83rem;font-weight:600;">
      {'故障注入器就绪' if injector_ok else '故障注入器未初始化'}
    </span>
  </div>
  <div style="display:flex;align-items:center;gap:8px;
              background:{'#0D3320' if monitor_ok else '#3A0E0E'};
              border:1px solid {'#16A34A' if monitor_ok else '#DC2626'};
              border-radius:8px;padding:8px 12px;">
    <span style="font-size:1rem;">{'✅' if monitor_ok else '❌'}</span>
    <span style="color:{'#4ADE80' if monitor_ok else '#FCA5A5'};
                 font-size:0.83rem;font-weight:600;">
      {'监控验证器就绪' if monitor_ok else '监控验证器未初始化'}
    </span>
  </div>
</div>
""",
            unsafe_allow_html=True,
        )

        # 演练进行中提示 + 紧急停止
        with _drill_tasks_lock:
            _running_tasks = [tid for tid, t in _drill_tasks.items() if t.get('status') == 'running']
        if _running_tasks:
            st.error(f"🔴 {len(_running_tasks)} 个演练进行中")
            if st.button("🛑 紧急停止所有演练", type="primary"):
                with _drill_tasks_lock:
                    for _tid in _running_tasks:
                        _drill_tasks[_tid]['stop_signal'] = True
                st.success("停止信号已发送")
        elif st.session_state.drill_in_progress:
            st.warning("⚡ 演练进行中，可安全切换页面")

        st.markdown("---")
        
        page = st.radio(
            "导航",
            ["🏠 首页", "🗂️ 集群资源", "⚡ 故障注入", "🔗 故障链", "📄 演练报告", "📊 监控面板", "⚙️ 设置"],
            label_visibility="collapsed"
        )

    # 页面路由
    if page == "🏠 首页":
        page_home()
    elif page == "🗂️ 集群资源":
        page_cluster_resources()
    elif page == "⚡ 故障注入":
        page_fault_injection()
    elif page == "🔗 故障链":
        page_chain_drill()
    elif page == "📄 演练报告":
        page_reports()
    elif page == "📊 监控面板":
        page_grafana()
    elif page == "⚙️ 设置":
        page_settings()


if __name__ == "__main__":
    main()
