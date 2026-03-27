"""
故障链演练页面模块
"""

import streamlit as st
import sys
import os
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

import db
from ..config import SCENARIO_MAP


def render():
    """渲染故障链演练页面"""
    st.title("🔗 多步骤故障链")

    st.info("💡 故障链功能：按顺序执行多个故障注入步骤，模拟复杂的故障场景")

    # 左右分栏
    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("📋 已保存的故障链")
        chains = db.list_drill_chains()

        if chains:
            for chain in chains:
                with st.expander(f"🔗 {chain['name']}"):
                    st.caption(chain.get('description', '无描述'))
                    stages = json.loads(chain.get('stages_json', '[]'))
                    st.write(f"包含 {len(stages)} 个步骤")

                    if st.button(f"🗑️ 删除", key=f"del_{chain['id']}"):
                        db.delete_drill_chain(chain['id'])
                        st.rerun()
        else:
            st.info("暂无保存的故障链")

    with col2:
        st.subheader("➕ 创建新故障链")

        chain_name = st.text_input("故障链名称", placeholder="例如：CPU+网络组合故障")
        chain_desc = st.text_area("描述", placeholder="描述这个故障链的目的...")

        st.write("**添加步骤：**")
        stage_type = st.selectbox("步骤类型", ["故障注入", "等待", "验证告警"])

        if stage_type == "故障注入":
            scenario = st.selectbox("故障场景", list(SCENARIO_MAP.keys()))
            namespace = st.text_input("命名空间", value="default")
            pod_selector = st.text_input("Pod 选择器", placeholder="app=nginx")
            duration = st.number_input("持续时间(秒)", min_value=10, value=60)

            if st.button("➕ 添加此步骤"):
                st.success("步骤已添加（功能开发中）")

        elif stage_type == "等待":
            wait_seconds = st.number_input("等待时间(秒)", min_value=1, value=30)
            if st.button("➕ 添加此步骤"):
                st.success("步骤已添加（功能开发中）")

        else:
            alert_name = st.text_input("告警名称")
            expected = st.selectbox("期望状态", ["firing", "resolved"])
            if st.button("➕ 添加此步骤"):
                st.success("步骤已添加（功能开发中）")

        st.markdown("---")

        if st.button("💾 保存故障链", type="primary", use_container_width=True):
            if not chain_name:
                st.warning("请输入故障链名称")
            else:
                st.info("保存功能开发中...")
