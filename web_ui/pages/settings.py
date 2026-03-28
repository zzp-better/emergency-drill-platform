"""
设置页面模块
"""

import streamlit as st
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

import db
from monitor_checker import MonitorChecker
from ..state import (
    init_session_state, get_chaos_injector, set_chaos_injector,
    get_monitor_checker, set_monitor_checker, get_cluster_config, set_cluster_config,
    get_monitor_config, set_monitor_config
)
from ..utils import init_chaos_injector, do_k8s_connect
from ..config import DEFAULT_CLUSTER, DEFAULT_MONITOR, DEFAULT_NOTIFY
from ..scheduler import get_scheduler, is_scheduler_available, reload_schedules_from_db


def render():
    """渲染设置页面"""
    init_session_state()
    
    st.title("⚙️ 设置")

    tab_cluster, tab_monitor, tab_notify, tab_schedule = st.tabs(
        ["🔗 集群连接", "📊 监控", "🔔 通知", "🗓️ 演练计划"]
    )

    with tab_cluster:
        _render_cluster_tab()
    
    with tab_monitor:
        _render_monitor_tab()
    
    with tab_notify:
        _render_notify_tab()
    
    with tab_schedule:
        _render_schedule_tab()


def _render_cluster_tab():
    """渲染集群连接标签页"""
    k8s_profiles = db.list_k8s_profiles()
    profile_names = [p['name'] for p in k8s_profiles]
    
    if profile_names:
        default_idx = next((i for i, p in enumerate(k8s_profiles) if p.get('is_default')), 0)
        selected_profile = st.selectbox("选择配置档案", profile_names, index=default_idx)
        if st.session_state.get('_k8s_sel') != selected_profile:
            st.session_state._k8s_sel = selected_profile
            loaded = db.get_k8s_profile(selected_profile)
            if loaded:
                set_cluster_config({**DEFAULT_CLUSTER, **loaded})
                set_chaos_injector(None)
    else:
        selected_profile = ""
        st.info("尚无已保存的配置档案，请填写下方配置并保存")
    
    st.markdown("---")
    
    # 连接状态展示
    cluster_config = get_cluster_config()
    if cluster_config.get('connected'):
        ci = cluster_config.get('cluster_info', {})
        c1, c2, c3 = st.columns(3)
        c1.metric("集群名称", ci.get('cluster_name', 'N/A'))
        c2.metric("K8s 版本", ci.get('kubernetes_version', 'N/A'))
        c3.metric("节点数量", ci.get('node_count', 'N/A'))
        
        injector = get_chaos_injector()
        inj_status = "就绪 ✓" if injector else "未初始化"
        st.success(f"✓ 集群已连接 | 故障注入器: {inj_status}")
    else:
        st.warning("⚠ 集群未连接")
    
    st.markdown("---")
    
    # 连接方式
    connection_type = st.radio(
        "连接方式",
        ["kubeconfig", "Token"],
        index=0 if cluster_config.get('connection_type', 'kubeconfig') == 'kubeconfig' else 1,
        horizontal=True
    )
    
    st.session_state.cluster_config['connection_type'] = connection_type
    
    if connection_type == "kubeconfig":
        kubeconfig_path = st.text_input(
            "Kubeconfig 路径",
            value=cluster_config.get('kubeconfig_path', os.path.expanduser('~/.kube/config')),
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
                value=cluster_config.get('api_server', ''),
                placeholder="https://192.168.1.100:6443",
            )
            st.session_state.cluster_config['api_server'] = api_server
        with c2:
            ca_cert = st.text_area(
                "CA 证书 (可选)",
                value=cluster_config.get('ca_cert', ''),
                height=100,
            )
            st.session_state.cluster_config['ca_cert'] = ca_cert
        token = st.text_area(
            "Service Account Token",
            value=cluster_config.get('token', ''),
            height=120,
        )
        st.session_state.cluster_config['token'] = token
    
    st.markdown("---")
    
    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("🔌 测试并连接", key="k8s_connect_btn", use_container_width=True, type="primary"):
            do_k8s_connect()
    with col_b:
        if st.button("🔄 重置配置", key="k8s_reset_btn", use_container_width=True):
            set_cluster_config({**DEFAULT_CLUSTER})
            set_chaos_injector(None)
            st.session_state._k8s_sel = None
            st.rerun()
    
    st.markdown("---")
    
    # 档案管理
    st.markdown('<p class="section-title">档案管理</p>', unsafe_allow_html=True)
    profile_name_input = st.text_input(
        "档案名称",
        value=selected_profile or "新配置",
        placeholder="为此配置命名",
        key="k8s_profile_name_input",
    )
    
    col_s, col_d, col_def = st.columns(3)
    with col_s:
        if st.button("💾 保存档案", key="k8s_save_btn", use_container_width=True):
            name = profile_name_input.strip()
            if name:
                config = dict(st.session_state.cluster_config)
                config.pop('connected', None)
                config.pop('cluster_info', None)
                db.save_k8s_profile(name, config)
                st.success(f"✓ 档案「{name}」已保存")
                st.rerun()
            else:
                st.warning("请输入档案名称")
    
    with col_d:
        if selected_profile and st.button("🗑 删除档案", key="del_k8s_profile", use_container_width=True):
            db.delete_k8s_profile(selected_profile)
            set_cluster_config({**DEFAULT_CLUSTER})
            set_chaos_injector(None)
            st.session_state._k8s_sel = None
            st.rerun()
    
    with col_def:
        if selected_profile and st.button("⭐ 设为默认", key="k8s_set_default_btn", use_container_width=True):
            db.set_default_k8s_profile(selected_profile)
            st.success(f"✓ 「{selected_profile}」已设为默认")
            st.rerun()


def _render_monitor_tab():
    """渲染监控标签页"""
    mon_profiles = db.list_monitor_profiles()
    mon_names = [p['name'] for p in mon_profiles]
    
    if mon_names:
        default_mon_idx = next((i for i, p in enumerate(mon_profiles) if p.get('is_default')), 0)
        selected_mon = st.selectbox("选择监控档案", mon_names, index=default_mon_idx)
        if st.session_state.get('_mon_sel') != selected_mon:
            st.session_state._mon_sel = selected_mon
            lm = db.get_monitor_profile(selected_mon)
            if lm:
                set_monitor_config({**DEFAULT_MONITOR, **lm})
                set_monitor_checker(None)
    else:
        selected_mon = ""
        st.info("尚无已保存的监控档案，请填写下方配置并保存")
    
    st.markdown("---")
    
    monitor_config = get_monitor_config()
    col1, col2 = st.columns(2)
    with col1:
        prometheus_url = st.text_input(
            "Prometheus URL",
            value=monitor_config.get('prometheus_url', 'http://localhost:9090'),
        )
    with col2:
        username = st.text_input(
            "用户名",
            value=monitor_config.get('username', ''),
            placeholder="可选",
        )
        password = st.text_input("密码", type="password", placeholder="可选（不会保存）")
    
    monitor_checker = get_monitor_checker()
    if monitor_checker is not None:
        st.success("✓ 监控已连接")
    else:
        st.warning("⚠ 监控未连接")
    
    st.markdown("---")
    
    col_ma, col_mb = st.columns(2)
    with col_ma:
        if st.button("🔌 连接监控", key="mon_connect_btn", use_container_width=True, type="primary"):
            try:
                set_monitor_checker(MonitorChecker(prometheus_url, username, password or None))
                monitor_config['prometheus_url'] = prometheus_url
                monitor_config['username'] = username
                st.success("✓ 监控已连接")
                st.rerun()
            except Exception as e:
                st.error(f"✗ 连接失败: {e}")
    with col_mb:
        if st.button("🔄 断开监控", key="mon_disconnect_btn", use_container_width=True):
            set_monitor_checker(None)
            st.rerun()
    
    st.markdown("---")
    
    # 档案管理
    st.markdown('<p class="section-title">档案管理</p>', unsafe_allow_html=True)
    mon_name_input = st.text_input(
        "档案名称",
        value=selected_mon or "默认监控",
        key="mon_profile_name_input",
    )
    
    col_ms, col_md, col_mdef = st.columns(3)
    with col_ms:
        if st.button("💾 保存监控档案", key="mon_save_btn", use_container_width=True):
            n = mon_name_input.strip()
            if n:
                config = dict(get_monitor_config())
                config.pop('connected', None)
                db.save_monitor_profile(n, config)
                st.success(f"✓ 档案「{n}」已保存")
                st.rerun()
            else:
                st.warning("请输入档案名称")
    with col_md:
        if selected_mon and st.button("🗑 删除档案", key="del_monitor_profile", use_container_width=True):
            db.delete_monitor_profile(selected_mon)
            set_monitor_config({**DEFAULT_MONITOR})
            set_monitor_checker(None)
            st.session_state._mon_sel = None
            st.rerun()
    with col_mdef:
        if selected_mon and st.button("⭐ 设为默认", key="mon_set_default_btn", use_container_width=True):
            db.set_default_monitor_profile(selected_mon)
            st.success(f"✓ 「{selected_mon}」已设为默认")
            st.rerun()


def _render_notify_tab():
    """渲染通知标签页"""
    st.caption("配置 Webhook 通知，当演练完成或失败时自动推送消息")
    
    notify_config = st.session_state.get('notify_config', DEFAULT_NOTIFY.copy())
    
    col1, col2 = st.columns(2)
    with col1:
        webhook_url = st.text_input(
            "Webhook URL",
            value=notify_config.get('webhook_url', ''),
            placeholder="https://webhook.example.com",
        )
    with col2:
        notify_enabled = st.checkbox(
            "启用通知",
            value=notify_config.get('enabled', False),
        )
    
    notify_config['webhook_url'] = webhook_url
    notify_config['enabled'] = notify_enabled
    st.session_state.notify_config = notify_config
    
    st.markdown("---")
    
    col_nsave, col_ntest = st.columns(2)
    with col_nsave:
        if st.button("💾 保存通知配置", key="notify_save_btn", use_container_width=True):
            db.save_notify_config(notify_config)
            st.success("✓ 通知配置已保存")
    with col_ntest:
        if webhook_url and st.button("🧪 测试通知", key="notify_test_btn", use_container_width=True):
            try:
                import requests as req
                payload = {
                    "text": "🔔 这是一条测试通知，来自应急演练平台"
                }
                resp = req.post(webhook_url, json=payload, timeout=10)
                if resp.status_code == 200:
                    st.success("✓ 测试通知发送成功")
                else:
                    st.error(f"✗ 发送失败: HTTP {resp.status_code}")
            except Exception as e:
                st.error(f"✗ 发送失败: {e}")


def _render_schedule_tab():
    """渲染演练计划标签页"""
    st.caption("配置定时演练计划，按 Cron 表达式自动触发（需保持应用运行)")
    
    scheduler = get_scheduler()
    if not is_scheduler_available():
        st.warning("⚠ APScheduler 未安装，定时演练功能不可用")
        return
    
    schedules = db.list_drill_schedules()
    
    if schedules:
        for s in schedules:
            enabled_icon = '✅' if s.get('enabled') else '⏸️'
            with st.expander(f"{enabled_icon} {s['name']}  |  `{s['cron_expr']}`  |  {s['scenario']}"):
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.text(f"**命名空间**: {s.get('namespace', 'default')}")
                    st.text(f"**Pod 选择器**: {s.get('pod_selector', '*')}")
                with col2:
                    st.text(f"**下次执行**: {s.get('next_run', 'N/A')}")
                    st.text(f"**上次执行**: {s.get('last_run', 'N/A')}")
                with col3:
                    if st.button("▶️ 启用" if not s.get('enabled') else "⏸️ 禁用", key=f"toggle_{s['name']}", use_container_width=True):
                        s['enabled'] = 0 if s['enabled'] else 1
                        db.update_schedule(s['name'], enabled=s['enabled'])
                        reload_schedules_from_db(db)
                        st.rerun()
    
    st.markdown("---")
    
    # 添加新计划
    st.markdown("#### 添加新计划")
    sn_col1, sn_col2 = st.columns(2)
    with sn_col1:
        schedule_name = st.text_input("计划名称", key="schedule_name")
    with sn_col2:
        cron_expr = st.text_input("Cron 表达式", placeholder="0 * * * *", key="cron_expr")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        scenario_type = st.selectbox(
            "演练场景",
            ["cpu_stress", "memory_stress", "network_delay", "disk_io", "pod_crash"],
            key="scenario_type",
        )
    with col2:
        namespace = st.text_input("命名空间", value="default", key="schedule_ns")
    with col3:
        pod_selector = st.text_input("Pod 选择器", placeholder="pod-name-prefix", key="pod_selector")
    
    if st.button("➕ 添加计划", key="schedule_add_btn", use_container_width=True, type="primary"):
        if not schedule_name or not cron_expr:
            st.warning("请填写计划名称和 Cron 表达式")
        else:
            try:
                schedule_data = {
                    'cron_expr': cron_expr,
                    'scenario': scenario_type,
                    'namespace': namespace,
                    'pod_selector': pod_selector,
                    'enabled': 1,
                }
                db.save_drill_schedule(schedule_name, schedule_data)
                reload_schedules_from_db(db)
                st.success(f"✓ 计划「{schedule_name}」已添加")
                st.rerun()
            except Exception as e:
                st.error(f"✗ 添加失败: {e}")
