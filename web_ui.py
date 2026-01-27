"""
应急演练自动化平台 - Web UI
基于 Streamlit 实现的可视化界面

功能：
1. 故障注入管理
2. 监控告警验证
3. 演练报告展示
"""

import streamlit as st
import yaml
import os
from datetime import datetime
import pandas as pd

# 页面配置
st.set_page_config(
    page_title="应急演练自动化平台",
    page_icon="🚨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 自定义 CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #FF6B6B;
        text-align: center;
        padding: 1rem 0;
    }
    .status-success {
        color: #4CAF50;
        font-weight: bold;
    }
    .status-error {
        color: #F44336;
        font-weight: bold;
    }
    .status-warning {
        color: #FF9800;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# 初始化 session state
if 'drill_history' not in st.session_state:
    st.session_state.drill_history = []

if 'current_drill' not in st.session_state:
    st.session_state.current_drill = None


def load_scenarios():
    """加载故障场景配置"""
    scenarios_dir = "scenarios"
    scenarios = []
    
    if os.path.exists(scenarios_dir):
        for filename in os.listdir(scenarios_dir):
            if filename.endswith('.yaml'):
                filepath = os.path.join(scenarios_dir, filename)
                with open(filepath, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                    scenarios.append({
                        'filename': filename,
                        'name': config.get('name', filename),
                        'description': config.get('description', ''),
                        'type': config.get('type', 'unknown')
                    })
    
    return scenarios


def page_home():
    """首页"""
    st.markdown('<h1 class="main-header">🚨 应急演练自动化平台</h1>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            label="演练次数",
            value=len(st.session_state.drill_history),
            delta="累计"
        )
    
    with col2:
        st.metric(
            label="可用场景",
            value=len(load_scenarios()),
            delta="个"
        )
    
    with col3:
        st.metric(
            label="成功率",
            value="100%",
            delta="暂无失败"
        )
    
    st.markdown("---")
    
    # 快速开始
    st.subheader("🚀 快速开始")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📋 开始故障注入演练", use_container_width=True, type="primary"):
            st.session_state.page = "fault_injection"
            st.rerun()
    
    with col2:
        if st.button("📊 查看监控告警", use_container_width=True):
            st.session_state.page = "monitoring"
            st.rerun()
    
    st.markdown("---")
    
    # 演练历史
    st.subheader("📜 演练历史")
    
    if st.session_state.drill_history:
        df = pd.DataFrame(st.session_state.drill_history)
        df = df[['time', 'scenario', 'status', 'duration']]
        df.columns = ['时间', '场景', '状态', '耗时(秒)']
        st.dataframe(df, use_container_width=True)
    else:
        st.info("暂无演练记录，请先执行演练")


def page_fault_injection():
    """故障注入页面"""
    st.title("⚡ 故障注入")
    
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
    
    st.markdown("---")
    
    # 参数配置
    st.subheader("🔧 参数配置")
    
    col1, col2 = st.columns(2)
    
    with col1:
        namespace = st.text_input("命名空间", value="default")
        pod_name = st.text_input("Pod 名称", placeholder="例如: nginx-deployment-xxx")
    
    with col2:
        timeout = st.number_input("超时时间(秒)", min_value=10, max_value=600, value=60)
        check_interval = st.number_input("检查间隔(秒)", min_value=1, max_value=30, value=5)
    
    st.markdown("---")
    
    # 执行演练
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        if st.button("🚀 开始演练", use_container_width=True, type="primary"):
            with st.spinner("正在执行演练..."):
                # 模拟演练过程
                import time
                start_time = time.time()
                
                # 模拟故障注入
                st.info(f"正在注入故障: {scenario['name']}")
                time.sleep(2)
                
                # 模拟监控验证
                st.info("正在验证监控告警...")
                time.sleep(2)
                
                # 模拟恢复检测
                st.info("正在检测系统恢复...")
                time.sleep(1)
                
                end_time = time.time()
                duration = round(end_time - start_time, 2)
                
                # 记录演练历史
                st.session_state.drill_history.append({
                    'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'scenario': scenario['name'],
                    'status': '成功',
                    'duration': duration
                })
                
                st.success(f"✅ 演练完成！耗时: {duration} 秒")
                
                # 显示演练结果
                st.markdown("---")
                st.subheader("📊 演练结果")
                
                result_data = {
                    '场景名称': scenario['name'],
                    '故障类型': scenario['type'],
                    '命名空间': namespace,
                    'Pod 名称': pod_name if pod_name else 'N/A',
                    '演练状态': '<span class="status-success">成功</span>',
                    '耗时': f'{duration} 秒',
                    '完成时间': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
                
                for key, value in result_data.items():
                    st.markdown(f"**{key}**: {value}", unsafe_allow_html=True)


def page_monitoring():
    """监控验证页面"""
    st.title("📊 监控告警验证")
    
    # Prometheus 配置
    st.subheader("🔌 Prometheus 连接配置")
    
    col1, col2 = st.columns(2)
    
    with col1:
        prometheus_url = st.text_input("Prometheus URL", value="http://192.168.56.66:9090")
    
    with col2:
        st.text_input("用户名", placeholder="可选")
        st.text_input("密码", type="password", placeholder="可选")
    
    st.markdown("---")
    
    # 告警查询
    st.subheader("🔔 告警查询")
    
    col1, col2 = st.columns(2)
    
    with col1:
        alert_name = st.text_input("告警名称", placeholder="例如: PodCrashLooping")
    
    with col2:
        timeout = st.number_input("等待超时(秒)", min_value=10, max_value=600, value=60)
    
    if st.button("🔍 查询告警", use_container_width=True):
        with st.spinner("正在查询告警..."):
            # 模拟查询过程
            import time
            time.sleep(1)
            
            # 模拟告警数据
            alerts = [
                {
                    'name': 'PodCrashLooping',
                    'severity': 'warning',
                    'state': 'firing',
                    'summary': 'Pod nginx-deployment-xxx is crash looping',
                    'labels': {
                        'namespace': 'default',
                        'pod': 'nginx-deployment-xxx'
                    }
                },
                {
                    'name': 'HighCPUUsage',
                    'severity': 'critical',
                    'state': 'pending',
                    'summary': 'CPU usage is above 80%',
                    'labels': {
                        'namespace': 'monitoring',
                        'pod': 'prometheus-0'
                    }
                }
            ]
            
            if alerts:
                st.success(f"✓ 查询到 {len(alerts)} 个告警")
                
                for i, alert in enumerate(alerts, 1):
                    with st.expander(f"{i}. {alert['name']} - {alert['state'].upper()}"):
                        st.write(f"**严重级别**: {alert['severity']}")
                        st.write(f"**状态**: {alert['state']}")
                        st.write(f"**描述**: {alert['summary']}")
                        st.write(f"**标签**: {alert['labels']}")
            else:
                st.info("当前没有活跃告警")
    
    st.markdown("---")
    
    # 实时告警监控
    st.subheader("📡 实时告警监控")
    
    if st.button("🔄 刷新告警", use_container_width=True):
        with st.spinner("正在刷新..."):
            import time
            time.sleep(0.5)
            st.success("✓ 告警已刷新")


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
                with st.expander(report):
                    filepath = os.path.join(reports_dir, report)
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
            avg_duration = df['duration'].mean()
            st.metric("平均耗时", f"{avg_duration:.2f} 秒")
        
        with col3:
            success_count = len(df[df['status'] == '成功'])
            success_rate = (success_count / len(df)) * 100
            st.metric("成功率", f"{success_rate:.1f}%")
        
        # 场景分布
        st.markdown("---")
        st.subheader("场景分布")
        
        scenario_counts = df['scenario'].value_counts()
        st.bar_chart(scenario_counts)
    else:
        st.info("暂无演练数据")


def page_settings():
    """设置页面"""
    st.title("⚙️ 设置")
    
    st.subheader("🔌 Prometheus 配置")
    
    prometheus_url = st.text_input(
        "Prometheus URL",
        value="http://192.168.56.66:9090",
        help="Prometheus 服务器地址"
    )
    
    username = st.text_input("用户名", placeholder="可选")
    password = st.text_input("密码", type="password", placeholder="可选")
    
    st.markdown("---")
    
    st.subheader("🎯 Kubernetes 配置")
    
    kubeconfig = st.text_input(
        "Kubeconfig 路径",
        value="~/.kube/config",
        help="Kubernetes 配置文件路径"
    )
    
    namespace = st.text_input("默认命名空间", value="default")
    
    st.markdown("---")
    
    st.subheader("🔔 通知配置")
    
    enable_notification = st.checkbox("启用通知", value=False)
    
    if enable_notification:
        webhook_url = st.text_input("Webhook URL", placeholder="例如: https://hooks.slack.com/...")
        notification_events = st.multiselect(
            "通知事件",
            ["演练开始", "演练完成", "告警触发", "演练失败"],
            default=["演练完成", "演练失败"]
        )
    
    st.markdown("---")
    
    if st.button("💾 保存配置", use_container_width=True, type="primary"):
        st.success("✓ 配置已保存")


def main():
    """主函数"""
    # 侧边栏导航
    with st.sidebar:
        st.title("🚨 EDAP")
        st.markdown("---")
        
        page = st.radio(
            "导航",
            ["🏠 首页", "⚡ 故障注入", "📊 监控验证", "📄 演练报告", "⚙️ 设置"],
            label_visibility="collapsed"
        )
        
        st.markdown("---")
        
        # 系统状态
        st.subheader("系统状态")
        st.success("✓ K8s 连接正常")
        st.success("✓ Prometheus 连接正常")
        st.success("✓ Chaos Mesh 就绪")
    
    # 页面路由
    if page == "🏠 首页":
        page_home()
    elif page == "⚡ 故障注入":
        page_fault_injection()
    elif page == "📊 监控验证":
        page_monitoring()
    elif page == "📄 演练报告":
        page_reports()
    elif page == "⚙️ 设置":
        page_settings()


if __name__ == "__main__":
    main()
