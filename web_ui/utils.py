"""
工具函数模块
包含通用工具函数和辅助功能
"""

import os
import re
import uuid
import yaml
import streamlit as st
from typing import Dict, Optional, List, Any
from datetime import datetime

import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from chaos_injector import ChaosInjector
from monitor_checker import MonitorChecker
import db

from .config import (
    DEFAULT_CLUSTER,
    DEFAULT_MONITOR,
    DEFAULT_GRAFANA,
    SCENARIO_MAP,
    CHAOS_MESH_SCENARIOS,
    CHAOS_TYPE_MAP,
)


from .state import (
    _drill_tasks,
    _drill_tasks_lock,
    get_drill_task,
    set_drill_task,
    get_chaos_injector,
    set_chaos_injector,
    get_monitor_checker,
    set_monitor_checker,
)


from .styles import apply_styles


def load_scenarios() -> List[Dict]:
    """
    加载故障场景配置

    Returns:
        List[Dict]: 场景配置列表
    """
    scenarios = []
    scenarios_dir = os.path.join(os.path.dirname(__file__), "..", "scenarios")

    if os.path.exists(scenarios_dir):
        for filename in os.listdir(scenarios_dir):
            if filename.endswith(".yaml") or filename.endswith(".yml"):
                # 安全检查：防止路径遍历攻击
                if ".." in filename or "/" in filename or "\\" in filename:
                    continue

                filepath = os.path.join(scenarios_dir, filename)

                # 验证文件路径在预期目录内
                abs_scenarios_dir = os.path.abspath(scenarios_dir)
                abs_filepath = os.path.abspath(filepath)
                if not abs_filepath.startswith(abs_scenarios_dir):
                    continue

                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        config = yaml.safe_load(f)
                        if config and isinstance(config, dict):
                            scenario = config.get("scenario", {})
                            target = config.get("target", {})
                            expected = config.get("expected", {})
                            fault = config.get("fault", {})
                            scenarios.append(
                                {
                                    "filename": filename,
                                    "name": scenario.get("name", filename),
                                    "description": scenario.get("description", ""),
                                    "type": scenario.get("type", "unknown"),
                                    "default_namespace": target.get(
                                        "namespace", "default"
                                    ),
                                    "default_pod_name": target.get("pod_name", ""),
                                    "expected_alert_name": expected.get(
                                        "alert_name", ""
                                    ),
                                    "expected_alert_timeout": expected.get(
                                        "alert_timeout", 180
                                    ),
                                    "fault_defaults": fault,
                                }
                            )
                except Exception as e:
                    st.warning(f"加载场景文件 {filename} 失败: {e}")
                    continue

    return scenarios


def validate_input(
    input_str: str, field_name: str, max_length: int = 253
) -> tuple[bool, str]:
    """
    验证用户输入

    Args:
        input_str: 输入字符串
        field_name: 字段名称
        max_length: 最大长度

    Returns:
        (bool, str): (是否有效, 错误消息)
    """
    if not input_str or not input_str.strip():
        return False, f"{field_name}不能为空"

    if len(input_str) > max_length:
        return False, f"{field_name}长度不能超过 {max_length} 个字符"

    # 检查 Kubernetes 资源名称规则（小写字母、数字、连字符）
    if not re.match(r"^[a-z0-9]([-a-z0-9]*[a-z0-9])?$", input_str):
        return (
            False,
            f"{field_name}只能包含小写字母、数字和连字符，且必须以字母或数字开头和结尾",
        )

    return True, ""


def build_injector(
    config: Optional[Dict] = None, use_chaos_mesh: bool = False
) -> Optional[ChaosInjector]:
    """
    从配置字典构建 ChaosInjector，成功返回实例，配置不完整或文件缺失返回 None
    """
    if config is None:
        config = st.session_state.cluster_config

    if config is None:
        return None

    try:
        conn_type = config.get("connection_type", "kubeconfig").lower()

        if conn_type == "token":
            api_server = config.get("api_server", "")
            token = config.get("token", "")
            if not api_server or not token:
                return None
            return ChaosInjector(
                use_chaos_mesh=use_chaos_mesh,
                cluster_api_server=api_server,
                cluster_token=token,
                cluster_ca_cert=config.get("ca_cert") or None,
            )
        else:
            kubeconfig_path = config.get(
                "kubeconfig_path", os.path.expanduser("~/.kube/config")
            )
            expanded = os.path.expanduser(kubeconfig_path) if kubeconfig_path else ""
            if not expanded or not os.path.exists(expanded):
                return None
            return ChaosInjector(
                use_chaos_mesh=use_chaos_mesh, kubeconfig_path=kubeconfig_path
            )
    except Exception as e:
        return None


def init_chaos_injector(use_chaos_mesh: bool = False, silent: bool = False) -> bool:
    """
    初始化故障注入器；silent=True 时不输出 st 消息

    Args:
        use_chaos_mesh: 是否使用 Chaos Mesh
        silent: 是否静默模式

    Returns:
        bool: 是否成功
    """
    if st.session_state.chaos_injector is not None:
        return True

    try:
        injector = build_injector(use_chaos_mesh=use_chaos_mesh)
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


def init_monitor_checker(
    prometheus_url: str, username: Optional[str] = None, password: Optional[str] = None
) -> bool:
    """
    初始化监控验证器

    Args:
        prometheus_url: Prometheus URL
        username: 用户名（可选)
        password: 密码（可选）

    Returns:
        bool: 是否成功
    """
    if st.session_state.monitor_checker is None:
        try:
            st.session_state.monitor_checker = MonitorChecker(
                prometheus_url, username, password
            )
            st.success("✓ 监控验证器初始化成功")
            return True
        except Exception as e:
            st.error(f"✗ 监控验证器初始化失败: {e}")
            return False
    return True


def format_duration(seconds: int) -> str:
    """
    格式化持续时间

    Args:
        seconds: 秒数

    Returns:
        格式化后的时间字符串
    """
    if seconds < 60:
        return f"{seconds}秒"
    elif seconds < 3600:
        return f"{seconds // 60} 分钟"
    elif seconds < 86400:
        return f"{seconds // 3600} 小时"
    else:
        return f"{seconds // 86400} 天"


def get_scenario_display_name(scenario: Dict) -> str:
    """
    获取场景显示名称

    Args:
        scenario: 场景配置字典

    Returns:
        显示名称
    """
    scenario_type = scenario.get("type", "unknown")
    return SCENARIO_MAP.get(scenario_type, {"name": scenario_type})["name"]


def run_health_check(namespace: str, pod_name: str, scenario_type: str) -> list[dict]:
    """
    演练前健康预检，返回检查项列表。
    每项格式: {'name': str, 'status': 'pass'|'warn'|'fail', 'message': str}

    Args:
        namespace: 命名空间
        pod_name: Pod 名称
        scenario_type: 场景类型

    Returns:
        list[dict]: 检查结果列表
    """
    injector = st.session_state.chaos_injector
    monitor = st.session_state.monitor_checker
    results = []

    # 1. 声名空间是否存在
    try:
        namespaces = injector.list_namespaces()
        if namespace in namespaces:
            results.append(
                {
                    "name": "命名空间存在",
                    "status": "pass",
                    "message": f'Namespace "{namespace}" 已找到',
                }
            )
        else:
            results.append(
                {
                    "name": "命名空间存在",
                    "status": "fail",
                    "message": f'Namespace "{namespace}" 不存在，可用命名空间: {", ".join(namespaces[:8])}',
                }
            )
    except Exception as e:
        results.append(
            {
                "name": "命名空间存在",
                "status": "warn",
                "message": f"无法查询命名空间列表: {e}",
            }
        )

    # 2. Pod 是否存在且处于 Running 状态
    try:
        pods = injector.list_pods(namespace)
        matched = [p for p in pods if p["name"] == pod_name]
        if not matched:
            results.append(
                {
                    "name": "Pod 状态",
                    "status": "fail",
                    "message": f'Pod "{pod_name}" 在命名空间 "{namespace}" 中不存在',
                }
            )
        else:
            pod_status = matched[0].get("status", "Unknown")
            if pod_status == "Running":
                results.append(
                    {
                        "name": "Pod 状态",
                        "status": "pass",
                        "message": f'Pod "{pod_name}" 当前状态: Running ✓',
                    }
                )
            else:
                results.append(
                    {
                        "name": "Pod 状态",
                        "status": "fail",
                        "message": f'Pod "{pod_name}" 当前状态: {pod_status}，不建议注入故障',
                    }
                )
    except Exception as e:
        results.append(
            {"name": "Pod 状态", "status": "warn", "message": f"无法查询 Pod 状态: {e}"}
        )

    # 3. pod_crash 场景： 检查是否有 Deployment 托管该 Pod
    if scenario_type == "pod_crash":
        try:
            deployments = injector.list_deployments(namespace)
            pods = injector.list_pods(namespace)
            matched = [p for p in pods if p["name"] == pod_name]
            has_owner = False
            if matched:
                for dep in deployments:
                    if pod_name.startswith(dep["name"] + "-"):
                        has_owner = True
                        results.append(
                            {
                                "name": "Deployment 托管检查",
                                "status": "pass",
                                "message": f'Pod 由 Deployment "{dep["name"]}" 托管，崩溃后可自动恢复',
                            }
                        )
                        break
            if not has_owner:
                results.append(
                    {
                        "name": "Deployment 托管检查",
                        "status": "warn",
                        "message": "Pod 可能不受 Deployment 托管，pod_crash 后可能无法自动恢复",
                    }
                )
        except Exception as e:
            results.append(
                {
                    "name": "Deployment 托管检查",
                    "status": "warn",
                    "message": f"无法验证 Deployment 托管关系: {e}",
                }
            )

    # 4. 是否已有活跃告警（避免干扰基线）
    if monitor is not None:
        try:
            alerts = monitor.prometheus.query_alerts()
            if alerts:
                alert_names = [
                    a.get("labels", {}).get("alertname", "未知") for a in alerts[:5]
                ]
                results.append(
                    {
                        "name": "活跃告警基线",
                        "status": "warn",
                        "message": f'当前已有 {len(alerts)} 个活跃告警（{", ".join(alert_names)}），可能干扰演练结果判断',
                    }
                )
            else:
                results.append(
                    {
                        "name": "活跃告警基线",
                        "status": "pass",
                        "message": "当前无活跃告警，基线干净",
                    }
                )
        except Exception as e:
            results.append(
                {
                    "name": "活跃告警基线",
                    "status": "warn",
                    "message": f"无法查询 Prometheus 告警: {e}",
                }
            )
    else:
        results.append(
            {
                "name": "活跃告警基线",
                "status": "warn",
                "message": "监控未配置，跳过告警基线检查",
            }
        )

    return results


def display_health_check(check_results: list[dict]) -> bool:
    """
    展示健康预检结果，返回是否存在 fail 级别的检查项。

    Args:
        check_results: 检查结果列表

    Returns:
        bool: 是否存在 fail 级别的检查项
    """
    icon_map = {"pass": "✅", "warn": "⚠️", "fail": "❌"}
    color_map = {
        "pass": "status-success",
        "warn": "status-warning",
        "fail": "status-error",
    }

    has_fail = any(r["status"] == "fail" for r in check_results)

    with st.expander("🩺 演练前健康预检结果", expanded=True):
        for item in check_results:
            icon = icon_map[item["status"]]
            css = color_map[item["status"]]
            st.markdown(
                f"{icon} **{item['name']}**  "
                f"<span class='{css}'>{item['message']}</span>",
                unsafe_allow_html=True,
            )
        if has_fail:
            st.error(
                "❌ 存在关键检查项未通过，建议修复后再执行演练。如确认要强制执行，请勾选下方选项。"
            )
        else:
            st.success("✅ 所有关键检查通过，可以开始演练")

    return has_fail


def send_notification(event: str, data: dict, _cfg: dict = None):
    """
    发送 Webhook 通知（异步，失败不影响主流程）

    Args:
        event: 事件名称
        data: 事件数据
        _cfg: 通知配置（可选，默认从 session state 获取）
    """
    cfg = _cfg if _cfg is not None else st.session_state.notify_config
    if not cfg.get("enabled"):
        return
    if event not in cfg.get("events", []):
        return
    url = cfg.get("webhook_url", "").strip()
    if not url:
        return

    import requests as _req

    try:
        payload = {
            "event": event,
            "platform": "EDAP",
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            **data,
        }
        _req.post(url, json=payload, timeout=5)
    except Exception:
        pass  # 通知失败静默处理，不影响演练流程


def generate_drill_report(
    scenario,
    namespace,
    pod_name,
    start_time,
    end_time,
    drill_duration,
    result,
    **kwargs,
):
    """
    生成演练报告并保存到 reports 目录

    Args:
        scenario: 场景配置
        namespace: 命名空间
        pod_name: Pod 名称
        start_time: 开始时间
        end_time: 结束时间
        drill_duration: 演练持续时间
        result: 演练结果

    Returns:
        str: 报告文件路径（成功时）或 None（失败时）
    """
    from .drill_reporting import generate_drill_report as _generate

    try:
        return _generate(
            scenario=scenario,
            namespace=namespace,
            pod_name=pod_name,
            start_time=start_time,
            end_time=end_time,
            drill_duration=drill_duration,
            result=result,
            **kwargs,
        )
    except Exception:
        return None


def do_k8s_connect():
    """测试并建立 k8s 连接，成功后自动初始化故障注入器"""
    config = st.session_state.cluster_config
    conn_type = config.get("connection_type", "kubeconfig").lower()
    try:
        if conn_type == "token":
            api_server_val = config.get("api_server", "")
            token_val = config.get("token", "")
            if not api_server_val or not token_val:
                st.error("请填写 API Server 地址和 Token")
                return
            test_injector = ChaosInjector(
                cluster_api_server=api_server_val,
                cluster_token=token_val,
                cluster_ca_cert=config.get("ca_cert") or None,
            )
        else:
            kp = config.get("kubeconfig_path", os.path.expanduser("~/.kube/config"))
            if not os.path.exists(os.path.expanduser(kp)):
                st.error("Kubeconfig 文件不存在")
                return
            test_injector = ChaosInjector(kubeconfig_path=kp)

        cluster_info = test_injector.get_cluster_info()
        st.session_state.cluster_config["connected"] = True
        st.session_state.cluster_config["cluster_info"] = cluster_info
        # 连接成功后直接复用此实例，无需二次初始化
        st.session_state.chaos_injector = test_injector
        st.success("✓ 集群连接成功，故障注入器已就绪！")
        if cluster_info.get("_errors"):
            st.warning("部分集群信息获取失败（不影响使用）")
    except Exception as e:
        st.error(f"✗ 连接失败: {e}")
        st.session_state.cluster_config["connected"] = False


def save_k8s_profile_action(name: str):
    """保存当前 k8s 配置为档案并设为默认"""
    name = (name or "").strip()
    if not name:
        st.error("请输入档案名称")
        return
    ok = db.save_k8s_profile(name, st.session_state.cluster_config, set_default=True)
    if ok:
        st.success(f"✓ 已保存档案「{name}」")
        st.rerun()
    else:
        st.error("保存失败，请重试")


def try_auto_connect():
    """启动时自动连接集群和初始化监控（如果已保存配置）"""
    if st.session_state.auto_connect_done:
        return

    st.session_state.auto_connect_done = True

    # 自动连接 K8s 集群
    if st.session_state.chaos_injector is None:
        cfg = st.session_state.cluster_config
        # 检查配置是否完整
        conn_type = cfg.get("connection_type", "kubeconfig").lower()
        can_connect = False

        if conn_type == "token":
            api_server = cfg.get("api_server", "")
            token = cfg.get("token", "")
            if api_server and token:
                can_connect = True
        else:
            kubeconfig_path = cfg.get("kubeconfig_path", "")
            if kubeconfig_path:
                expanded = os.path.expanduser(kubeconfig_path)
                if os.path.exists(expanded):
                    can_connect = True

        if can_connect:
            try:
                injector = build_injector(config=cfg, use_chaos_mesh=False)
                if injector:
                    # 测试连接
                    cluster_info = injector.get_cluster_info()
                    st.session_state.cluster_config["connected"] = True
                    st.session_state.cluster_config["cluster_info"] = cluster_info
                    st.session_state.chaos_injector = injector
            except Exception:
                # 自动连接失败不显示错误，用户可以手动连接
                pass

    # 自动初始化监控检查器
    if st.session_state.monitor_checker is None:
        mon_cfg = st.session_state.monitor_config
        prom_url = mon_cfg.get("prometheus_url", "")
        if prom_url:
            try:
                username = mon_cfg.get("username") or None
                password = mon_cfg.get("password") or None
                st.session_state.monitor_checker = MonitorChecker(
                    prom_url, username, password
                )
            except Exception:
                pass
