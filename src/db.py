"""
SQLite 数据库管理模块
管理 k8s 连接配置档案、监控配置档案和演练历史
"""
import sqlite3
import json
import os
from typing import Optional, List, Dict

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'edap.db')

# 旧 JSON 文件路径（用于一次性迁移）
_OLD_CONFIG  = os.path.join(os.path.dirname(__file__), '..', 'data', 'cluster_config.json')
_OLD_MONITOR = os.path.join(os.path.dirname(__file__), '..', 'data', 'monitor_config.json')
_OLD_HISTORY = os.path.join(os.path.dirname(__file__), '..', 'data', 'drill_history.json')


def _get_conn() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """初始化数据库：建表 + 从旧 JSON 迁移数据（仅首次）"""
    with _get_conn() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS k8s_profiles (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                name            TEXT NOT NULL UNIQUE,
                is_default      INTEGER NOT NULL DEFAULT 0,
                connection_type TEXT NOT NULL DEFAULT 'kubeconfig',
                kubeconfig_path TEXT NOT NULL DEFAULT '',
                api_server      TEXT NOT NULL DEFAULT '',
                token           TEXT NOT NULL DEFAULT '',
                ca_cert         TEXT NOT NULL DEFAULT '',
                created_at      TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS monitor_profiles (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                name           TEXT NOT NULL UNIQUE,
                is_default     INTEGER NOT NULL DEFAULT 0,
                prometheus_url TEXT NOT NULL DEFAULT 'http://localhost:9090',
                username       TEXT NOT NULL DEFAULT '',
                password       TEXT NOT NULL DEFAULT '',
                created_at     TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at     TEXT NOT NULL DEFAULT (datetime('now'))
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS drill_history (
                id       INTEGER PRIMARY KEY AUTOINCREMENT,
                time     TEXT NOT NULL,
                scenario TEXT NOT NULL,
                status   TEXT NOT NULL,
                duration REAL NOT NULL DEFAULT 0,
                message  TEXT NOT NULL DEFAULT ''
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS drill_schedules (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                name         TEXT NOT NULL UNIQUE,
                enabled      INTEGER NOT NULL DEFAULT 1,
                cron_expr    TEXT NOT NULL,
                scenario     TEXT NOT NULL,
                namespace    TEXT NOT NULL DEFAULT 'default',
                pod_selector TEXT NOT NULL DEFAULT '',
                params_json  TEXT NOT NULL DEFAULT '{}',
                next_run     TEXT,
                last_run     TEXT,
                created_at   TEXT NOT NULL DEFAULT (datetime('now'))
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS drill_chains (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                name        TEXT NOT NULL UNIQUE,
                description TEXT NOT NULL DEFAULT '',
                stages_json TEXT NOT NULL DEFAULT '[]',
                created_at  TEXT NOT NULL DEFAULT (datetime('now'))
            )
        ''')
        conn.commit()

    _migrate_json()


def _migrate_json():
    """将旧 JSON 文件一次性迁移到 SQLite"""
    # k8s 配置迁移
    if os.path.exists(_OLD_CONFIG):
        try:
            with open(_OLD_CONFIG, 'r', encoding='utf-8') as f:
                cfg = json.load(f)
            if cfg:
                with _get_conn() as conn:
                    count = conn.execute('SELECT COUNT(*) FROM k8s_profiles').fetchone()[0]
                if count == 0:
                    save_k8s_profile('默认配置', cfg, set_default=True)
        except Exception:
            pass

    # 监控配置迁移
    if os.path.exists(_OLD_MONITOR):
        try:
            with open(_OLD_MONITOR, 'r', encoding='utf-8') as f:
                cfg = json.load(f)
            if cfg and cfg.get('prometheus_url'):
                with _get_conn() as conn:
                    count = conn.execute('SELECT COUNT(*) FROM monitor_profiles').fetchone()[0]
                if count == 0:
                    save_monitor_profile('默认监控', cfg, set_default=True)
        except Exception:
            pass

    # 演练历史迁移
    if os.path.exists(_OLD_HISTORY):
        try:
            with open(_OLD_HISTORY, 'r', encoding='utf-8') as f:
                history = json.load(f)
            if history:
                with _get_conn() as conn:
                    count = conn.execute('SELECT COUNT(*) FROM drill_history').fetchone()[0]
                    if count == 0:
                        for entry in history:
                            conn.execute(
                                'INSERT INTO drill_history (time, scenario, status, duration, message) '
                                'VALUES (?,?,?,?,?)',
                                (entry.get('time', ''), entry.get('scenario', ''),
                                 entry.get('status', ''), entry.get('duration', 0),
                                 entry.get('message', ''))
                            )
                        conn.commit()
        except Exception:
            pass


# ── k8s profiles ──────────────────────────────────────────────────────────────

def list_k8s_profiles() -> List[Dict]:
    with _get_conn() as conn:
        rows = conn.execute(
            'SELECT * FROM k8s_profiles ORDER BY is_default DESC, updated_at DESC'
        ).fetchall()
        return [dict(r) for r in rows]


def get_default_k8s_profile() -> Optional[Dict]:
    with _get_conn() as conn:
        row = conn.execute(
            'SELECT * FROM k8s_profiles WHERE is_default = 1 ORDER BY updated_at DESC LIMIT 1'
        ).fetchone()
        if not row:
            row = conn.execute(
                'SELECT * FROM k8s_profiles ORDER BY updated_at DESC LIMIT 1'
            ).fetchone()
        return dict(row) if row else None


def get_k8s_profile(name: str) -> Optional[Dict]:
    with _get_conn() as conn:
        row = conn.execute(
            'SELECT * FROM k8s_profiles WHERE name = ?', (name,)
        ).fetchone()
        return dict(row) if row else None


def save_k8s_profile(name: str, config: dict, set_default: bool = False) -> bool:
    try:
        with _get_conn() as conn:
            conn.execute('''
                INSERT INTO k8s_profiles
                    (name, is_default, connection_type, kubeconfig_path, api_server, token, ca_cert, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))
                ON CONFLICT(name) DO UPDATE SET
                    is_default      = excluded.is_default,
                    connection_type = excluded.connection_type,
                    kubeconfig_path = excluded.kubeconfig_path,
                    api_server      = excluded.api_server,
                    token           = excluded.token,
                    ca_cert         = excluded.ca_cert,
                    updated_at      = excluded.updated_at
            ''', (
                name,
                1 if set_default else 0,
                config.get('connection_type', 'kubeconfig'),
                config.get('kubeconfig_path', ''),
                config.get('api_server', ''),
                config.get('token', ''),
                config.get('ca_cert', ''),
            ))
            if set_default:
                conn.execute(
                    'UPDATE k8s_profiles SET is_default = 0 WHERE name != ?', (name,)
                )
            conn.commit()
        return True
    except Exception:
        return False


def delete_k8s_profile(name: str):
    with _get_conn() as conn:
        conn.execute('DELETE FROM k8s_profiles WHERE name = ?', (name,))
        conn.commit()


def set_default_k8s_profile(name: str):
    with _get_conn() as conn:
        conn.execute('UPDATE k8s_profiles SET is_default = 0')
        conn.execute(
            "UPDATE k8s_profiles SET is_default = 1, updated_at = datetime('now') WHERE name = ?",
            (name,)
        )
        conn.commit()


# ── monitor profiles ──────────────────────────────────────────────────────────

def list_monitor_profiles() -> List[Dict]:
    with _get_conn() as conn:
        rows = conn.execute(
            'SELECT * FROM monitor_profiles ORDER BY is_default DESC, updated_at DESC'
        ).fetchall()
        return [dict(r) for r in rows]


def get_default_monitor_profile() -> Optional[Dict]:
    with _get_conn() as conn:
        row = conn.execute(
            'SELECT * FROM monitor_profiles WHERE is_default = 1 ORDER BY updated_at DESC LIMIT 1'
        ).fetchone()
        if not row:
            row = conn.execute(
                'SELECT * FROM monitor_profiles ORDER BY updated_at DESC LIMIT 1'
            ).fetchone()
        return dict(row) if row else None


def get_monitor_profile(name: str) -> Optional[Dict]:
    with _get_conn() as conn:
        row = conn.execute(
            'SELECT * FROM monitor_profiles WHERE name = ?', (name,)
        ).fetchone()
        return dict(row) if row else None


def save_monitor_profile(name: str, config: dict, set_default: bool = False) -> bool:
    try:
        with _get_conn() as conn:
            conn.execute('''
                INSERT INTO monitor_profiles
                    (name, is_default, prometheus_url, username, password, updated_at)
                VALUES (?, ?, ?, ?, ?, datetime('now'))
                ON CONFLICT(name) DO UPDATE SET
                    is_default     = excluded.is_default,
                    prometheus_url = excluded.prometheus_url,
                    username       = excluded.username,
                    password       = excluded.password,
                    updated_at     = excluded.updated_at
            ''', (
                name,
                1 if set_default else 0,
                config.get('prometheus_url', 'http://localhost:9090'),
                config.get('username', ''),
                config.get('password', ''),
            ))
            if set_default:
                conn.execute(
                    'UPDATE monitor_profiles SET is_default = 0 WHERE name != ?', (name,)
                )
            conn.commit()
        return True
    except Exception:
        return False


def delete_monitor_profile(name: str):
    with _get_conn() as conn:
        conn.execute('DELETE FROM monitor_profiles WHERE name = ?', (name,))
        conn.commit()


def set_default_monitor_profile(name: str):
    with _get_conn() as conn:
        conn.execute('UPDATE monitor_profiles SET is_default = 0')
        conn.execute(
            "UPDATE monitor_profiles SET is_default = 1, updated_at = datetime('now') WHERE name = ?",
            (name,)
        )
        conn.commit()


# ── drill history ─────────────────────────────────────────────────────────────

def append_drill_history(entry: dict):
    with _get_conn() as conn:
        conn.execute(
            'INSERT INTO drill_history (time, scenario, status, duration, message) VALUES (?,?,?,?,?)',
            (entry.get('time', ''), entry.get('scenario', ''),
             entry.get('status', ''), entry.get('duration', 0),
             entry.get('message', ''))
        )
        conn.commit()


def load_drill_history() -> List[Dict]:
    with _get_conn() as conn:
        rows = conn.execute(
            'SELECT * FROM drill_history ORDER BY id DESC'
        ).fetchall()
        return [dict(r) for r in rows]


# ── drill schedules ───────────────────────────────────────────────────────────

def list_drill_schedules() -> List[Dict]:
    with _get_conn() as conn:
        rows = conn.execute(
            'SELECT * FROM drill_schedules ORDER BY created_at DESC'
        ).fetchall()
        return [dict(r) for r in rows]


def get_drill_schedule(name: str) -> Optional[Dict]:
    with _get_conn() as conn:
        row = conn.execute(
            'SELECT * FROM drill_schedules WHERE name = ?', (name,)
        ).fetchone()
        return dict(row) if row else None


def save_drill_schedule(name: str, config: dict) -> bool:
    try:
        with _get_conn() as conn:
            conn.execute('''
                INSERT INTO drill_schedules
                    (name, enabled, cron_expr, scenario, namespace, pod_selector, params_json, next_run)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(name) DO UPDATE SET
                    enabled      = excluded.enabled,
                    cron_expr    = excluded.cron_expr,
                    scenario     = excluded.scenario,
                    namespace    = excluded.namespace,
                    pod_selector = excluded.pod_selector,
                    params_json  = excluded.params_json,
                    next_run     = excluded.next_run
            ''', (
                name,
                1 if config.get('enabled', True) else 0,
                config.get('cron_expr', '0 2 * * *'),
                config.get('scenario', 'cpu_stress'),
                config.get('namespace', 'default'),
                config.get('pod_selector', ''),
                config.get('params_json', '{}'),
                config.get('next_run'),
            ))
            conn.commit()
        return True
    except Exception:
        return False


def delete_drill_schedule(name: str):
    with _get_conn() as conn:
        conn.execute('DELETE FROM drill_schedules WHERE name = ?', (name,))
        conn.commit()


def update_schedule(name: str, enabled: int):
    """更新演练计划的启用状态"""
    with _get_conn() as conn:
        conn.execute(
            'UPDATE drill_schedules SET enabled = ? WHERE name = ?',
            (enabled, name)
        )
        conn.commit()


def save_notify_config(config: dict) -> bool:
    """保存通知配置到数据库（使用 app_settings 键值表）"""
    try:
        with _get_conn() as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS app_settings (
                    key   TEXT PRIMARY KEY,
                    value TEXT NOT NULL DEFAULT ''
                )
            ''')
            conn.execute('''
                INSERT INTO app_settings (key, value) VALUES ('notify_config', ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
            ''', (json.dumps(config, ensure_ascii=False),))
            conn.commit()
        return True
    except Exception:
        return False


def load_notify_config() -> Optional[dict]:
    """从数据库加载通知配置"""
    try:
        with _get_conn() as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS app_settings (
                    key   TEXT PRIMARY KEY,
                    value TEXT NOT NULL DEFAULT ''
                )
            ''')
            row = conn.execute(
                "SELECT value FROM app_settings WHERE key = 'notify_config'"
            ).fetchone()
            if row:
                return json.loads(row[0])
    except Exception:
        pass
    return None


def update_schedule_run_time(name: str, next_run: Optional[str], last_run: Optional[str] = None):
    with _get_conn() as conn:
        if last_run:
            conn.execute(
                'UPDATE drill_schedules SET next_run = ?, last_run = ? WHERE name = ?',
                (next_run, last_run, name)
            )
        else:
            conn.execute(
                'UPDATE drill_schedules SET next_run = ? WHERE name = ?',
                (next_run, name)
            )
        conn.commit()


# ── drill chains ──────────────────────────────────────────────────────────────

def list_drill_chains() -> List[Dict]:
    with _get_conn() as conn:
        rows = conn.execute(
            'SELECT * FROM drill_chains ORDER BY created_at DESC'
        ).fetchall()
        return [dict(r) for r in rows]


def get_drill_chain(name: str) -> Optional[Dict]:
    with _get_conn() as conn:
        row = conn.execute(
            'SELECT * FROM drill_chains WHERE name = ?', (name,)
        ).fetchone()
        return dict(row) if row else None


def save_drill_chain(name: str, description: str, stages: list) -> bool:
    try:
        with _get_conn() as conn:
            conn.execute('''
                INSERT INTO drill_chains (name, description, stages_json)
                VALUES (?, ?, ?)
                ON CONFLICT(name) DO UPDATE SET
                    description = excluded.description,
                    stages_json = excluded.stages_json
            ''', (name, description, json.dumps(stages, ensure_ascii=False)))
            conn.commit()
        return True
    except Exception:
        return False


def delete_drill_chain(name: str):
    with _get_conn() as conn:
        conn.execute('DELETE FROM drill_chains WHERE name = ?', (name,))
        conn.commit()
