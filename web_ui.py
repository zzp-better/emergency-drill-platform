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
import sys
from datetime import datetime
import pandas as pd

# 添加 src 目录到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from chaos_injector import ChaosInjector
from monitor_checker import MonitorChecker

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

if 'chaos_injector' not in st.session_state:
    st.session_state.chaos_injector = None

if 'monitor_checker' not in st.session_state:
    st.session_state.monitor_checker = None


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


def init_chaos_injector(use_chaos_mesh=False):
    """初始化故障注入器"""
    if st.session_state.chaos_injector is None:
        try:
            st.session_state.chaos_injector = ChaosInjector(use_chaos_mesh=use_chaos_mesh)
            st.success("✓ 故障注入器初始化成功")
            return True
        except Exception as e:
            st.error(f"✗ 故障注入器初始化失败: {e}")
            return False
    return True


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
        success_count = len([d for d in st.session_state.drill_history if d.get('status') == '成功'])
        if st.session_state.drill_history:
            success_rate = (success_count / len(st.session_state.drill_history)) * 100
            st.metric(
                label="成功率",
                value=f"{success_rate:.1f}%",
                delta=f"{success_count}/{len(st.session_state.drill_history)}"
            )
        else:
            st.metric(
                label="成功率",
                value="N/A",
                delta="暂无数据"
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
        if not df.empty:
            # 选择要显示的列
            display_cols = ['time', 'scenario', 'status', 'duration']
            if all(col in df.columns for col in display_cols):
                df_display = df[display_cols]
                df_display.columns = ['时间', '场景', '状态', '耗时(秒)']
                st.dataframe(df_display, use_container_width=True)
            else:
                st.dataframe(df, use_container_width=True)
    else:
        st.info("暂无演练记录，请先执行演练")


def page_fault_injection():
    """故障注入页面"""
    st.title("⚡ 故障注入")
    
    # 初始化故障注入器
    with st.expander("⚙️ 故障注入器配置", expanded=True):
        use_chaos_mesh = st.checkbox("使用 Chaos Mesh", value=False, help="启用后可使用更多故障场景")
        
        if st.button("🔄 初始化故障注入器"):
            if init_chaos_injector(use_chaos_mesh):
                st.rerun()
    
    if st.session_state.chaos_injector is None:
        st.warning("请先初始化故障注入器")
        return
    
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
            # 验证输入
            if not pod_name or not pod_name.strip():
                st.error("❌ Pod 名称不能为空")
                return

            # 验证 namespace
            is_valid, error_msg = validate_input(namespace, "命名空间")
            if not is_valid:
                st.error(f"❌ {error_msg}")
                return

            # 验证 pod_name（Pod 名称可以包含更多字符）
            if not pod_name.strip():
                st.error("❌ Pod 名称不能为空")
                return

            with st.spinner("正在执行演练..."):
                start_time = datetime.now()
                
                # 根据场景类型执行故障注入
                result = None
                scenario_type = scenario['type']
                
                try:
                    if scenario_type == 'pod_crash':
                        result = st.session_state.chaos_injector.delete_pod(namespace, pod_name)
                    elif scenario_type == 'cpu_stress':
                        result = st.session_state.chaos_injector.inject_cpu_stress(
                            namespace=namespace,
                            pod_name=pod_name,
                            cpu_count=2,  # 默认使用 2 个 CPU 核心
                            memory_size='100Mi',  # 默认压测 100Mi 内存
                            duration='60s'
                        )
                    elif scenario_type == 'network_delay':
                        result = st.session_state.chaos_injector.inject_network_delay(
                            namespace=namespace,
                            pod_name=pod_name,
                            latency='100ms',  # 默认延迟 100ms
                            jitter='10ms',    # 默认抖动 10ms
                            duration='60s'
                        )
                    elif scenario_type == 'disk_io':
                        result = st.session_state.chaos_injector.inject_disk_failure(
                            namespace=namespace,
                            pod_name=pod_name,
                            path='/var/log',      # 默认路径
                            fault_type='disk_fill',  # 默认故障类型：磁盘填充
                            size='1Gi',           # 默认填充 1Gi
                            duration='60s'
                        )
                    else:
                        st.error(f"未知的场景类型: {scenario_type}")
                        return
                    
                    end_time = datetime.now()
                    duration = (end_time - start_time).total_seconds()
                    
                    # 记录演练历史
                    st.session_state.drill_history.append({
                        'time': start_time.strftime('%Y-%m-%d %H:%M:%S'),
                        'scenario': scenario['name'],
                        'status': '成功' if result.get('success', False) else '失败',
                        'duration': round(duration, 2),
                        'message': result.get('message', '')
                    })
                    
                    if result.get('success', False):
                        st.success(f"✅ 演练完成！耗时: {duration:.2f} 秒")
                    else:
                        st.error(f"❌ 演练失败: {result.get('message', '未知错误')}")
                    
                    # 显示演练结果
                    st.markdown("---")
                    st.subheader("📊 演练结果")
                    
                    result_data = {
                        '场景名称': scenario['name'],
                        '故障类型': scenario['type'],
                        '命名空间': namespace,
                        'Pod 名称': pod_name if pod_name else 'N/A',
                        '演练状态': '<span class="status-success">成功</span>' if result.get('success', False) else '<span class="status-error">失败</span>',
                        '耗时': f'{duration:.2f} 秒',
                        '完成时间': end_time.strftime('%Y-%m-%d %H:%M:%S')
                    }
                    
                    for key, value in result_data.items():
                        st.markdown(f"**{key}**: {value}", unsafe_allow_html=True)
                    
                    # 显示详细信息
                    if result.get('recovery_time'):
                        st.info(f"📈 Pod 恢复时间: {result['recovery_time']} 秒")
                    
                    if result.get('message'):
                        st.info(f"💬 消息: {result['message']}")
                
                except Exception as e:
                    st.error(f"❌ 演练执行出错: {e}")
                    import traceback
                    st.error(traceback.format_exc())


def page_monitoring():
    """监控验证页面"""
    st.title("📊 监控告警验证")
    
    # Prometheus 配置
    st.subheader("🔌 Prometheus 连接配置")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # 从环境变量读取默认值，如果没有则使用默认值
        default_prometheus_url = os.environ.get('PROMETHEUS_URL', 'http://localhost:9090')
        prometheus_url = st.text_input("Prometheus URL", value=default_prometheus_url)
    
    with col2:
        username = st.text_input("用户名", placeholder="可选")
        password = st.text_input("密码", type="password", placeholder="可选")
    
    if st.button("🔄 初始化监控验证器"):
        if init_monitor_checker(prometheus_url, username, password):
            st.rerun()
    
    if st.session_state.monitor_checker is None:
        st.warning("请先初始化监控验证器")
        return
    
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
            # 查询告警
            alert = st.session_state.monitor_checker.prometheus.query_alert_by_name(alert_name)
            
            if alert:
                st.success(f"✓ 找到告警: {alert_name}")
                
                labels = alert.get('labels', {})
                with st.expander(f"📋 告警详情", expanded=True):
                    st.write(f"**告警名称**: {labels.get('alertname', 'N/A')}")
                    st.write(f"**严重级别**: {labels.get('severity', 'N/A')}")
                    st.write(f"**状态**: {alert.get('state', 'N/A')}")
                    st.write(f"**描述**: {alert.get('annotations', {}).get('summary', 'N/A')}")
                    st.write(f"**标签**: {labels}")
            else:
                st.info(f"未找到告警: {alert_name}")
    
    st.markdown("---")
    
    # 查询所有告警
    col1, col2 = st.columns([2, 1])
    
    with col1:
        if st.button("📡 查询所有告警", use_container_width=True):
            with st.spinner("正在查询所有告警..."):
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
            with st.spinner("正在刷新..."):
                st.success("✓ 告警已刷新")
                st.rerun()


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
    
    use_chaos_mesh = st.checkbox("使用 Chaos Mesh", value=False, help="启用后可使用更多故障场景")
    
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
        
        # 重新初始化组件
        if st.session_state.chaos_injector is not None or st.session_state.monitor_checker is not None:
            st.session_state.chaos_injector = None
            st.session_state.monitor_checker = None
            st.info("组件已重置，请重新初始化")


def main():
    """主函数"""
    # 侧边栏导航
    with st.sidebar:
        st.title("🚨 EDAP")
        st.markdown("---")
        
        # 系统状态
        st.subheader("系统状态")
        if st.session_state.chaos_injector is not None:
            st.success("✓ 故障注入器就绪")
        else:
            st.warning("⚠ 故障注入器未初始化")
        
        if st.session_state.monitor_checker is not None:
            st.success("✓ 监控验证器就绪")
        else:
            st.warning("⚠ 监控验证器未初始化")
        
        st.markdown("---")
        
        page = st.radio(
            "导航",
            ["🏠 首页", "⚡ 故障注入", "📊 监控验证", "📄 演练报告", "⚙️ 设置"],
            label_visibility="collapsed"
        )
    
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
