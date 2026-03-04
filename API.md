# API 参考文档 (API.md)

## 目录

- [概述](#概述)
- [故障注入 API](#故障注入-api)
- [监控验证 API](#监控验证-api)
- [配置文件格式](#配置文件格式)
- [返回值格式](#返回值格式)
- [错误处理](#错误处理)
- [使用示例](#使用示例)

---

## 概述

应急演练自动化平台提供了一套完整的 Python API，用于故障注入、监控验证和报告生成。本文档详细描述了所有公开 API 的使用方法。

### 快速开始

```python
from src.chaos_injector import ChaosInjector
from src.monitor_checker import MonitorChecker

# 初始化故障注入器
injector = ChaosInjector(use_chaos_mesh=False)

# 初始化监控验证器
checker = MonitorChecker(prometheus_url="http://localhost:9090")

# 执行故障注入
result = injector.delete_pod("default", "nginx-xxx")

# 验证告警
alert_result = checker.wait_for_alert("PodCrashLooping", timeout=60)
```

---

## 故障注入 API

### ChaosInjector

故障注入器类，提供统一的故障注入接口。

#### 初始化

```python
ChaosInjector(use_chaos_mesh: bool = False)
```

**参数**:
- `use_chaos_mesh` (bool, 可选): 是否使用 Chaos Mesh。默认 `False`

**返回**: ChaosInjector 实例

**异常**:
- `Exception`: Kubernetes 客户端初始化失败

**示例**:
```python
# 使用原生 Kubernetes
injector = ChaosInjector()

# 使用 Chaos Mesh
injector = ChaosInjector(use_chaos_mesh=True)
```

---

### delete_pod()

删除指定 Pod，模拟崩溃故障。

```python
delete_pod(namespace: str, pod_name: str) -> Dict
```

**参数**:
- `namespace` (str): Kubernetes 命名空间
- `pod_name` (str): Pod 名称

**返回**: Dict
```python
{
    "scenario": "pod_crash",
    "namespace": "default",
    "pod_name": "nginx-xxx",
    "inject_time": "2026-01-29 10:00:00",
    "success": True,
    "recovery_time": 25,  # 秒
    "message": "Pod 删除成功"
}
```

**示例**:
```python
result = injector.delete_pod("default", "nginx-deployment-7d5c6d8b9f-abc12")

if result["success"]:
    print(f"Pod 删除成功，恢复时间: {result['recovery_time']} 秒")
else:
    print(f"Pod 删除失败: {result['message']}")
```

---

### inject_cpu_stress()

注入 CPU/内存压测故障（需要 Chaos Mesh）。

```python
inject_cpu_stress(
    namespace: str,
    pod_name: str,
    cpu_count: Optional[int] = None,
    memory_size: Optional[str] = None,
    duration: str = "60s"
) -> Dict
```

**参数**:
- `namespace` (str): Kubernetes 命名空间
- `pod_name` (str): 目标 Pod 名称
- `cpu_count` (int, 可选): CPU 核心数。例如: `2`
- `memory_size` (str, 可选): 内存大小。支持格式: `100Mi`, `1Gi`, `104857600`（字节）
- `duration` (str): 持续时间。例如: `60s`, `5m`, `1h`

**返回**: Dict
```python
{
    "scenario": "cpu_stress",
    "namespace": "default",
    "pod_name": "app-xxx",
    "success": True,
    "chaos_name": "cpu-stress-xxx",
    "duration": "60s",
    "message": "CPU 压测故障注入成功"
}
```

**示例**:
```python
# CPU 压测
result = injector.inject_cpu_stress(
    namespace="default",
    pod_name="app-deployment-xxx",
    cpu_count=2,
    duration="120s"
)

# CPU + 内存压测
result = injector.inject_cpu_stress(
    namespace="default",
    pod_name="app-deployment-xxx",
    cpu_count=2,
    memory_size="200Mi",
    duration="120s"
)
```

---

### inject_network_delay()

注入网络延迟故障（需要 Chaos Mesh）。

```python
inject_network_delay(
    namespace: str,
    pod_name: str,
    latency: str = "100ms",
    jitter: str = "10ms",
    duration: str = "60s"
) -> Dict
```

**参数**:
- `namespace` (str): Kubernetes 命名空间
- `pod_name` (str): 目标 Pod 名称
- `latency` (str): 延迟时间。例如: `100ms`, `1s`
- `jitter` (str): 抖动时间。例如: `10ms`, `50ms`
- `duration` (str): 持续时间

**返回**: Dict
```python
{
    "scenario": "network_delay",
    "namespace": "default",
    "pod_name": "app-xxx",
    "success": True,
    "chaos_name": "network-delay-xxx",
    "latency": "100ms",
    "jitter": "10ms",
    "duration": "60s",
    "message": "网络延迟故障注入成功"
}
```

**示例**:
```python
result = injector.inject_network_delay(
    namespace="default",
    pod_name="web-service-xxx",
    latency="200ms",
    jitter="50ms",
    duration="300s"
)
```

---

### inject_disk_failure()

注入磁盘故障（需要 Chaos Mesh）。

```python
inject_disk_failure(
    namespace: str,
    pod_name: str,
    path: str = "/var/log",
    fault_type: str = "disk_fill",
    size: str = "1Gi",
    duration: str = "60s"
) -> Dict
```

**参数**:
- `namespace` (str): Kubernetes 命名空间
- `pod_name` (str): 目标 Pod 名称
- `path` (str): 目标路径
- `fault_type` (str): 故障类型。可选值: `disk_fill`, `disk_read_error`, `disk_write_error`
- `size` (str): 填充大小（仅 `disk_fill` 类型）。例如: `1Gi`, `500Mi`
- `duration` (str): 持续时间

**返回**: Dict
```python
{
    "scenario": "disk_failure",
    "namespace": "default",
    "pod_name": "app-xxx",
    "success": True,
    "chaos_name": "disk-failure-xxx",
    "fault_type": "disk_fill",
    "path": "/var/log",
    "size": "1Gi",
    "duration": "60s",
    "message": "磁盘故障注入成功"
}
```

**示例**:
```python
# 磁盘填充
result = injector.inject_disk_failure(
    namespace="default",
    pod_name="database-xxx",
    path="/data",
    fault_type="disk_fill",
    size="2Gi",
    duration="180s"
)

# 磁盘读写错误
result = injector.inject_disk_failure(
    namespace="default",
    pod_name="app-xxx",
    path="/var/log",
    fault_type="disk_write_error",
    duration="60s"
)
```

---

### inject_from_config()

根据配置文件注入故障。

```python
inject_from_config(config_path: str) -> Dict
```

**参数**:
- `config_path` (str): 配置文件路径（YAML 格式）

**返回**: Dict（根据场景类型返回相应的结果）

**示例**:
```python
# 从配置文件注入
result = injector.inject_from_config("scenarios/cpu_stress.yaml")

if result["success"]:
    print(f"故障注入成功: {result['message']}")
```

---

### list_pods()

列出指定命名空间的所有 Pod。

```python
list_pods(namespace: str) -> List[Dict]
```

**参数**:
- `namespace` (str): Kubernetes 命名空间

**返回**: List[Dict]
```python
[
    {
        "name": "nginx-deployment-xxx",
        "status": "Running",
        "node": "node-1",
        "created": "2026-01-29T10:00:00Z"
    },
    ...
]
```

**示例**:
```python
pods = injector.list_pods("default")

for pod in pods:
    print(f"Pod: {pod['name']}, Status: {pod['status']}")
```

---

## 监控验证 API

### PrometheusClient

Prometheus 客户端类，封装 Prometheus HTTP API。

#### 初始化

```python
PrometheusClient(
    url: str,
    username: Optional[str] = None,
    password: Optional[str] = None
)
```

**参数**:
- `url` (str): Prometheus 地址。例如: `http://localhost:9090`
- `username` (str, 可选): 用户名（基本认证）
- `password` (str, 可选): 密码（基本认证）

**返回**: PrometheusClient 实例

**示例**:
```python
# 无认证
client = PrometheusClient("http://localhost:9090")

# 基本认证
client = PrometheusClient(
    "http://prometheus.example.com",
    username="admin",
    password="secret"
)
```

---

### query_alerts()

查询当前所有活跃的告警。

```python
query_alerts() -> List[Dict]
```

**返回**: List[Dict]
```python
[
    {
        "labels": {
            "alertname": "PodCrashLooping",
            "severity": "critical",
            "namespace": "default",
            "pod": "nginx-xxx"
        },
        "annotations": {
            "summary": "Pod is crash looping",
            "description": "Pod nginx-xxx has restarted 5 times"
        },
        "state": "firing",
        "activeAt": "2026-01-29T10:00:00Z",
        "value": "5"
    },
    ...
]
```

**示例**:
```python
alerts = client.query_alerts()

print(f"当前活跃告警数: {len(alerts)}")

for alert in alerts:
    labels = alert.get('labels', {})
    print(f"告警: {labels.get('alertname')}, 严重级别: {labels.get('severity')}")
```

---

### query_alert_by_name()

查询指定名称的告警。

```python
query_alert_by_name(alert_name: str) -> Optional[Dict]
```

**参数**:
- `alert_name` (str): 告警名称

**返回**: Dict 或 None
```python
{
    "labels": {
        "alertname": "PodCrashLooping",
        "severity": "critical"
    },
    "state": "firing",
    ...
}
```

**示例**:
```python
alert = client.query_alert_by_name("PodCrashLooping")

if alert:
    print(f"告警状态: {alert['state']}")
else:
    print("告警未触发")
```

---

### query_metrics()

执行 PromQL 查询。

```python
query_metrics(query: str) -> Dict
```

**参数**:
- `query` (str): PromQL 查询语句

**返回**: Dict
```python
{
    "resultType": "vector",
    "result": [
        {
            "metric": {
                "namespace": "default",
                "pod": "nginx-xxx"
            },
            "value": [1706515200, "5"]
        },
        ...
    ]
}
```

**示例**:
```python
# 查询 Pod 重启次数
result = client.query_metrics(
    'kube_pod_container_status_restarts_total{namespace="default"}'
)

for item in result.get('result', []):
    metric = item['metric']
    value = item['value'][1]
    print(f"Pod: {metric['pod']}, 重启次数: {value}")
```

---

### MonitorChecker

监控验证器类，提供告警验证功能。

#### 初始化

```python
MonitorChecker(
    prometheus_url: str,
    username: Optional[str] = None,
    password: Optional[str] = None
)
```

**参数**:
- `prometheus_url` (str): Prometheus 地址
- `username` (str, 可选): 用户名
- `password` (str, 可选): 密码

**返回**: MonitorChecker 实例

**示例**:
```python
checker = MonitorChecker("http://localhost:9090")
```

---

### wait_for_alert()

等待指定告警触发。

```python
wait_for_alert(
    alert_name: str,
    timeout: int = 300,
    check_interval: int = 10
) -> Dict
```

**参数**:
- `alert_name` (str): 告警名称
- `timeout` (int): 超时时间（秒）。默认 300
- `check_interval` (int): 检查间隔（秒）。默认 10

**返回**: Dict
```python
{
    "alert_name": "PodCrashLooping",
    "triggered": True,
    "trigger_time": "2026-01-29 10:00:15",
    "wait_time": 15,  # 秒
    "alert_details": {...},
    "message": "告警在 15 秒后触发"
}
```

**示例**:
```python
result = checker.wait_for_alert(
    alert_name="HighCPUUsage",
    timeout=120,
    check_interval=5
)

if result["triggered"]:
    print(f"✅ 告警已触发，等待时间: {result['wait_time']} 秒")
else:
    print(f"❌ 告警未触发: {result['message']}")
```

---

### verify_alert_exists()

验证告警是否存在（立即检查）。

```python
verify_alert_exists(alert_name: str) -> bool
```

**参数**:
- `alert_name` (str): 告警名称

**返回**: bool

**示例**:
```python
if checker.verify_alert_exists("PodCrashLooping"):
    print("告警已触发")
else:
    print("告警未触发")
```

---

### check_pod_metrics()

检查 Pod 相关指标。

```python
check_pod_metrics(namespace: str, pod_name: str) -> Dict
```

**参数**:
- `namespace` (str): 命名空间
- `pod_name` (str): Pod 名称（支持通配符）

**返回**: Dict
```python
{
    "restart_count": [...],
    "pod_status": [...]
}
```

**示例**:
```python
metrics = checker.check_pod_metrics("default", "nginx-deployment")

print(f"Pod 指标: {metrics}")
```

---

## 配置文件格式

### 场景配置文件结构

所有场景配置文件使用 YAML 格式，存放在 `scenarios/` 目录。

#### 基本结构

```yaml
scenario:
  name: "场景名称"
  type: "场景类型"
  description: "场景描述"

target:
  namespace: "命名空间"
  pod_name: "Pod 名称"

fault:
  # 故障参数（根据场景类型不同）

validation:
  alert_name: "预期告警名称"
  timeout: 120
```

---

### Pod 崩溃场景

**文件**: `scenarios/pod_crash.yaml`

```yaml
scenario:
  name: "Pod 崩溃演练"
  type: "pod_crash"
  description: "删除 Pod，验证自动重启和告警"

target:
  namespace: "default"
  pod_name: "nginx-deployment-xxx"

validation:
  alert_name: "PodCrashLooping"
  timeout: 120
  check_interval: 10
```

---

### CPU 压测场景

**文件**: `scenarios/cpu_stress.yaml`

```yaml
scenario:
  name: "CPU 压测演练"
  type: "cpu_stress"
  description: "模拟 CPU 资源耗尽"

target:
  namespace: "default"
  pod_name: "app-deployment-xxx"

fault:
  duration: "120s"
  cpu:
    workers: 2  # CPU 核心数
  memory:
    enabled: true
    size: "200Mi"  # 内存大小

validation:
  alert_name: "HighCPUUsage"
  timeout: 180
  check_interval: 10
```

---

### 网络延迟场景

**文件**: `scenarios/network_delay.yaml`

```yaml
scenario:
  name: "网络延迟演练"
  type: "network_delay"
  description: "模拟网络延迟和抖动"

target:
  namespace: "default"
  pod_name: "web-service-xxx"

fault:
  duration: "180s"
  network:
    latency: "200ms"  # 延迟时间
    jitter: "50ms"    # 抖动时间
    correlation: "50" # 相关性（可选）

validation:
  alert_name: "HighNetworkLatency"
  timeout: 240
  check_interval: 15
```

---

### 磁盘故障场景

**文件**: `scenarios/disk_io.yaml`

```yaml
scenario:
  name: "磁盘 IO 故障演练"
  type: "disk_io"
  description: "模拟磁盘空间不足"

target:
  namespace: "default"
  pod_name: "database-xxx"

fault:
  duration: "300s"
  fault_type: "disk_fill"  # disk_fill, disk_read_error, disk_write_error
  fill:
    path: "/data"
    size: "2Gi"

validation:
  alert_name: "DiskSpaceLow"
  timeout: 360
  check_interval: 20
```

---

## 返回值格式

### 成功响应

所有 API 在成功时返回包含 `success: True` 的字典：

```python
{
    "success": True,
    "scenario": "场景类型",
    "message": "操作成功消息",
    # ... 其他字段
}
```

### 失败响应

失败时返回包含 `success: False` 的字典：

```python
{
    "success": False,
    "scenario": "场景类型",
    "message": "错误消息",
    # ... 其他字段
}
```

---

## 错误处理

### 异常类型

#### Kubernetes API 异常

```python
from kubernetes.client.rest import ApiException

try:
    result = injector.delete_pod("default", "non-existent-pod")
except ApiException as e:
    print(f"Kubernetes API 错误: {e.status} - {e.reason}")
```

#### Prometheus 连接异常

```python
import requests

try:
    alerts = client.query_alerts()
except requests.exceptions.RequestException as e:
    print(f"Prometheus 连接失败: {e}")
```

#### 配置文件异常

```python
try:
    result = injector.inject_from_config("invalid.yaml")
except FileNotFoundError:
    print("配置文件不存在")
except yaml.YAMLError as e:
    print(f"YAML 解析错误: {e}")
```

---

## 使用示例

### 示例 1: 完整的故障演练流程

```python
from src.chaos_injector import ChaosInjector
from src.monitor_checker import MonitorChecker
from datetime import datetime

# 1. 初始化
injector = ChaosInjector()
checker = MonitorChecker("http://localhost:9090")

# 2. 执行故障注入
print("开始故障注入...")
inject_result = injector.delete_pod("default", "nginx-deployment-xxx")

if not inject_result["success"]:
    print(f"故障注入失败: {inject_result['message']}")
    exit(1)

print(f"✅ 故障注入成功")

# 3. 验证告警
print("等待告警触发...")
alert_result = checker.wait_for_alert(
    alert_name="PodCrashLooping",
    timeout=120,
    check_interval=5
)

if alert_result["triggered"]:
    print(f"✅ 告警已触发，等待时间: {alert_result['wait_time']} 秒")
else:
    print(f"❌ 告警未触发: {alert_result['message']}")

# 4. 生成报告
report = f"""
# 应急演练报告

## 基本信息
- 演练时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- 场景: Pod 崩溃演练
- 目标: {inject_result['namespace']}/{inject_result['pod_name']}

## 故障注入
- 注入时间: {inject_result['inject_time']}
- 注入结果: {'成功' if inject_result['success'] else '失败'}
- 恢复时间: {inject_result.get('recovery_time', 'N/A')} 秒

## 监控验证
- 预期告警: {alert_result['alert_name']}
- 告警触发: {'是' if alert_result['triggered'] else '否'}
- 触发时间: {alert_result.get('trigger_time', 'N/A')}
- 等待时长: {alert_result['wait_time']} 秒

## 结论
{'✅ 演练成功' if inject_result['success'] and alert_result['triggered'] else '❌ 演练失败'}
"""

print(report)

# 保存报告
with open(f"reports/drill_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md", "w") as f:
    f.write(report)
```

---

### 示例 2: 使用配置文件批量演练

```python
import os
from src.chaos_injector import ChaosInjector

injector = ChaosInjector(use_chaos_mesh=True)

# 获取所有场景配置
scenarios_dir = "scenarios"
scenario_files = [f for f in os.listdir(scenarios_dir) if f.endswith('.yaml')]

results = []

for scenario_file in scenario_files:
    print(f"\n执行场景: {scenario_file}")

    config_path = os.path.join(scenarios_dir, scenario_file)
    result = injector.inject_from_config(config_path)

    results.append({
        "scenario": scenario_file,
        "success": result.get("success", False),
        "message": result.get("message", "")
    })

    print(f"结果: {'✅ 成功' if result['success'] else '❌ 失败'}")

# 统计结果
total = len(results)
success = sum(1 for r in results if r["success"])

print(f"\n总计: {total} 个场景")
print(f"成功: {success} 个")
print(f"失败: {total - success} 个")
print(f"成功率: {(success/total)*100:.1f}%")
```

---

### 示例 3: 监控多个告警

```python
from src.monitor_checker import MonitorChecker
import time

checker = MonitorChecker("http://localhost:9090")

# 要监控的告警列表
alert_names = [
    "PodCrashLooping",
    "HighCPUUsage",
    "HighMemoryUsage",
    "DiskSpaceLow"
]

print("开始监控告警...")

while True:
    print(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}]")

    for alert_name in alert_names:
        exists = checker.verify_alert_exists(alert_name)
        status = "🔴 触发" if exists else "🟢 正常"
        print(f"{alert_name}: {status}")

    time.sleep(30)  # 每 30 秒检查一次
```

---

### 示例 4: Chaos Mesh 高级故障注入

```python
from src.chaos_injector import ChaosInjector

injector = ChaosInjector(use_chaos_mesh=True)

# CPU 压测
print("1. CPU 压测...")
result = injector.inject_cpu_stress(
    namespace="default",
    pod_name="app-deployment-xxx",
    cpu_count=4,
    memory_size="500Mi",
    duration="300s"
)
print(f"结果: {result['message']}")

# 网络延迟
print("\n2. 网络延迟...")
result = injector.inject_network_delay(
    namespace="default",
    pod_name="web-service-xxx",
    latency="500ms",
    jitter="100ms",
    duration="300s"
)
print(f"结果: {result['message']}")

# 磁盘故障
print("\n3. 磁盘故障...")
result = injector.inject_disk_failure(
    namespace="default",
    pod_name="database-xxx",
    path="/data",
    fault_type="disk_fill",
    size="5Gi",
    duration="300s"
)
print(f"结果: {result['message']}")
```

---

### 示例 5: 自定义告警验证逻辑

```python
from src.monitor_checker import MonitorChecker
import time

checker = MonitorChecker("http://localhost:9090")

def wait_for_multiple_alerts(alert_names, timeout=300):
    """等待多个告警同时触发"""
    start_time = time.time()
    triggered_alerts = set()

    while time.time() - start_time < timeout:
        for alert_name in alert_names:
            if alert_name not in triggered_alerts:
                if checker.verify_alert_exists(alert_name):
                    triggered_alerts.add(alert_name)
                    print(f"✅ 告警触发: {alert_name}")

        if len(triggered_alerts) == len(alert_names):
            return True, triggered_alerts

        time.sleep(5)

    return False, triggered_alerts

# 使用示例
alert_names = ["HighCPUUsage", "HighMemoryUsage"]
success, triggered = wait_for_multiple_alerts(alert_names, timeout=180)

if success:
    print(f"✅ 所有告警已触发: {triggered}")
else:
    print(f"❌ 部分告警未触发，已触发: {triggered}")
```

---

## 最佳实践

### 1. 错误处理

始终使用 try-except 处理可能的异常：

```python
try:
    result = injector.delete_pod("default", "pod-name")
    if result["success"]:
        print("成功")
    else:
        print(f"失败: {result['message']}")
except Exception as e:
    print(f"异常: {e}")
```

### 2. 超时设置

根据实际情况设置合理的超时时间：

```python
# 快速验证（开发环境）
result = checker.wait_for_alert("Alert", timeout=60)

# 生产环境（告警可能需要更长时间）
result = checker.wait_for_alert("Alert", timeout=300)
```

### 3. 日志记录

使用 Python logging 模块记录操作：

```python
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

logger.info("开始故障注入")
result = injector.delete_pod("default", "pod-name")
logger.info(f"故障注入结果: {result}")
```

### 4. 资源清理

确保在演练后清理 Chaos Mesh 资源：

```python
# Chaos Mesh 会根据 duration 自动清理
# 如需手动清理，可以删除 Chaos 资源
```

---

## 相关文档

- [DEPLOYMENT.md](DEPLOYMENT.md) - 部署指南
- [ARCHITECTURE.md](ARCHITECTURE.md) - 架构设计
- [README.md](README.md) - 项目概述

---

**最后更新**: 2026-01-29
**版本**: v1.0.0
**作者**: 应急运维工程师
