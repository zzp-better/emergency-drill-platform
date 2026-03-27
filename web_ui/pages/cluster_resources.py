"""
集群资源页面模块
"""

import streamlit as st
import pandas as pd
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from ..state import get_chaos_injector, init_session_state


def render():
    """渲染集群资源页面"""
    init_session_state()
    
    st.title("🗂️ 集群资源")

    injector = get_chaos_injector()
    if injector is None:
        st.warning("⚠ 集群未连接，请先在「⚙️ 设置」页面配置并连接集群")
        return

    # 顶部工具栏
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

    # 汇总指标
    all_pods = []
    all_deps = []
    load_errors = []

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
    m2.metric("Running", len(running_pods), delta=f"✓" if not not_running else None)
    m3.metric("非 Running", len(not_running))
    m4.metric("Deployment", len(filtered_deps))

    st.markdown("---")

    # Pod 列表 和 Deployment 列表
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
