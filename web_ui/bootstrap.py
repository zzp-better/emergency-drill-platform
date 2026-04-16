"""
应用启动初始化模块
负责启动时的会话级自动连接和进程级调度恢复。
"""

from __future__ import annotations

import streamlit as st

_PROCESS_RUNTIME_DONE = False


def initialize_runtime() -> None:
    """初始化应用运行时依赖。"""
    import db

    from .scheduler import reload_schedules_from_db
    from .utils import try_auto_connect

    global _PROCESS_RUNTIME_DONE

    if not _PROCESS_RUNTIME_DONE:
        reload_schedules_from_db(db)
        _PROCESS_RUNTIME_DONE = True

    if st.session_state.get("_session_runtime_done"):
        return

    try_auto_connect()
    st.session_state["_session_runtime_done"] = True
