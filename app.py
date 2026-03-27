"""
应急演练智能平台 - 主入口
使用模块化 web_ui 包
"""

import streamlit as st
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# 导入模块化组件
from web_ui import PAGE_CONFIG, NAVIGATION_MENU, apply_styles, init_session_state
from web_ui.pages import home, cluster_resources, fault_injection, chain_drill, reports, settings, monitor

# 初始化数据库
import db
db.init_db()

# 页面配置
st.set_page_config(**PAGE_CONFIG)

# 应用样式
apply_styles()

# 初始化会话状态
init_session_state()

# 侧边栏导航
st.sidebar.markdown(
    '<div style="font-size:1.4rem;font-weight:800;color:#FFFFFF;">应急演练智能平台</div>'
    '<div style="font-size:0.7rem;color:#64748B;">Emergency Drill Platform</div>',
    unsafe_allow_html=True
)
st.sidebar.markdown("---")

page = st.sidebar.radio("导航", NAVIGATION_MENU, label_visibility="collapsed")

# 路由到对应页面
if page == '🏠 首页':
    home.render()
elif page == '🗂️ 集群资源':
    cluster_resources.render()
elif page == '⚡ 故障注入':
    fault_injection.render()
elif page == '🔗 故障链':
    chain_drill.render()
elif page == '📄 演练报告':
    reports.render()
elif page == '⚙️ 设置':
    settings.render()
elif page == '📊 监控面板':
    monitor.render()
