# Chaos Mesh 集成指南

## 概述

应急演练自动化平台已集成 Chaos Mesh，支持更丰富的故障注入场景。Chaos Mesh 是一个云原生的混沌工程平台，可以模拟各种故障场景，帮助验证系统的韧性。

## 支持的故障场景

### 1. CPU 压测

模拟 CPU 资源耗尽，验证系统在高负载下的表现。

**适用场景**：
- 验证应用在高 CPU 使用率下的性能
- 测试自动扩缩容是否正常工作
- 验证监控告警是否及时触发

**配置示例**：
```python
from chaos_injector import ChaosInjector

injector = ChaosInjector(use_chaos_mesh=True)

result = injector.inject_cpu_stress(
    namespace="default",
    pod_name="my-app-xxx-xxx",
    cpu_count=2,        # 使用 2 个 CPU 核心
    memory_size="100Mi", # 同时压测 100Mi 内存
    duration="60s"      # 持续 60 秒
)
```

**配置文件方式**：
```yaml
scenario:
  name: "CPU 压力测试演练"
  type: "cpu_stress"
  engine: "chaos_mesh"

target:
  namespace: "default"
  pod_name: "my-app-xxx-xxx"

fault:
  cpu:
    workers: 2
    load: 100
  memory:
    enabled: true
    size: "100Mi"
  duration: "60s"
```

---

### 2. 网络延迟

模拟网络延迟，验证系统在网络不稳定情况下的表现。

**适用场景**：
- 验证应用对网络延迟的容忍度
- 测试超时配置是否合理
- 验证重试机制是否正常工作

**配置示例**：
```python
from chaos_injector import ChaosInjector

injector = ChaosInjector(use_chaos_mesh=True)

result = injector.inject_network_delay(
    namespace="default",
    pod_name="my-app-xxx-xxx",
    latency="100ms",    # 延迟 100 毫秒
    jitter="10ms",      # 抖动 10 毫秒
    duration="60s"      # 持续 60 秒
)
```

**配置文件方式**：
```yaml
scenario:
  name: "网络延迟演练"
  type: "network_delay"
  engine: "chaos_mesh"

target:
  namespace: "default"
  pod_name: "my-app-xxx-xxx"

fault:
  network:
    latency: "100ms"
    jitter: "10ms"
    direction: "to"
  duration: "60s"
```

---

### 3. 网络丢包

模拟网络丢包，验证系统在数据丢失情况下的表现。

**适用场景**：
- 验证应用对网络丢包的容忍度
- 测试数据传输的可靠性
- 验证容错机制是否正常工作

**配置示例**：
```python
from chaos_mesh_injector import ChaosMeshInjector

injector = ChaosMeshInjector()

result = injector.create_network_loss(
    namespace="default",
    pod_name="my-app-xxx-xxx",
    loss="50%",         # 丢包率 50%
    correlation="0",     # 相关性 0
    duration="60s"      # 持续 60 秒
)
```

---

### 4. 磁盘故障

模拟磁盘空间不足或读写错误，验证系统在存储问题下的表现。

**适用场景**：
- 验证应用对磁盘空间不足的处理
- 测试日志轮转是否正常工作
- 验证监控告警是否及时触发

**配置示例**：
```python
from chaos_injector import ChaosInjector

injector = ChaosInjector(use_chaos_mesh=True)

# 磁盘填充
result = injector.inject_disk_failure(
    namespace="default",
    pod_name="my-app-xxx-xxx",
    path="/var/log",
    fault_type="disk_fill",
    size="1Gi",         # 填充 1GB
    duration="60s"
)

# 磁盘读错误
result = injector.inject_disk_failure(
    namespace="default",
    pod_name="my-app-xxx-xxx",
    fault_type="disk_read_error",
    duration="60s"
)

# 磁盘写错误
result = injector.inject_disk_failure(
    namespace="default",
    pod_name="my-app-xxx-xxx",
    fault_type="disk_write_error",
    duration="60s"
)
```

**配置文件方式**：
```yaml
scenario:
  name: "磁盘 IO 故障演练"
  type: "disk_io"
  engine: "chaos_mesh"

target:
  namespace: "default"
  pod_name: "my-app-xxx-xxx"

fault:
  fault_type: "disk_fill"
  fill:
    path: "/var/log"
    size: "1Gi"
  duration: "60s"
```

---

### 5. Pod 杀死

模拟 Pod 崩溃，验证系统自愈能力。

**配置示例**：
```python
from chaos_mesh_injector import ChaosMeshInjector

injector = ChaosMeshInjector()

result = injector.create_pod_kill(
    namespace="default",
    pod_name="my-app-xxx-xxx",
    grace_period=0     # 立即终止
)
```

---

## 完整演练流程

### 使用配置文件

```python
from chaos_injector import ChaosInjector
from monitor_checker import MonitorChecker

# 初始化组件
injector = ChaosInjector(use_chaos_mesh=True)
checker = MonitorChecker("http://localhost:9090")

# 从配置文件注入故障
inject_result = injector.inject_from_config("scenarios/cpu_stress.yaml")

# 验证监控告警
alert_result = checker.wait_for_alert(
    alert_name="HighCPUUsage",
    timeout=180
)

# 生成报告
print(f"故障注入: {inject_result['success']}")
print(f"告警触发: {alert_result['triggered']}")
```

### 使用示例脚本

```bash
# 运行 Chaos Mesh 演练示例
python examples/chaos_mesh_drill.py
```

选择要运行的演练：
1. CPU 压测演练
2. 网络延迟演练
3. 磁盘故障演练
4. 从配置文件注入故障
5. 完整的 Chaos Mesh 演练流程

---

## Chaos Mesh 安装

### 前置条件

- Kubernetes 集群（1.12+）
- kubectl 已配置
- Helm 3.x

### 安装步骤

```bash
# 添加 Chaos Mesh Helm 仓库
helm repo add chaos-mesh https://charts.chaos-mesh.org
helm repo update

# 创建命名空间
kubectl create namespace chaos-mesh

# 安装 Chaos Mesh
helm install chaos-mesh chaos-mesh/chaos-mesh -n chaos-mesh --version 2.6.1

# 验证安装
kubectl get pod -n chaos-mesh
```

### 卸载步骤

```bash
# 卸载 Chaos Mesh
helm uninstall chaos-mesh -n chaos-mesh

# 删除命名空间
kubectl delete namespace chaos-mesh
```

详细安装指南：https://chaos-mesh.org/docs/installation

---

## 最佳实践

### 1. 演练前准备

- **备份重要数据**：确保演练不会影响生产数据
- **通知相关人员**：提前通知团队成员，避免误解
- **选择合适时间**：在业务低峰期进行演练
- **准备回滚方案**：确保出现问题时能快速恢复

### 2. 演练执行

- **从小到大**：从简单的故障开始，逐步增加复杂度
- **记录日志**：详细记录演练过程和结果
- **监控告警**：实时监控告警触发情况
- **及时止损**：如果影响超出预期，立即停止演练

### 3. 演练后分析

- **生成报告**：使用平台自动生成演练报告
- **分析结果**：评估系统表现是否符合预期
- **优化改进**：根据演练结果优化系统配置
- **总结经验**：记录演练经验，形成知识库

---

## 常见问题

### Q1: Chaos Mesh 故障注入失败怎么办？

**A**: 检查以下几点：
1. Chaos Mesh 是否正确安装：`kubectl get pod -n chaos-mesh`
2. 是否有足够的权限：检查 RBAC 配置
3. 目标 Pod 是否存在：`kubectl get pod -n <namespace>`
4. 查看日志：`kubectl logs -n chaos-mesh <chaos-mesh-pod>`

### Q2: 如何验证故障是否生效？

**A**: 可以通过以下方式验证：
1. 查看目标 Pod 的资源使用情况：`kubectl top pod`
2. 检查 Pod 日志：`kubectl logs <pod-name>`
3. 使用 Prometheus 查询相关指标
4. 观察告警是否触发

### Q3: 故障持续时间设置多长合适？

**A**: 建议根据实际情况设置：
- **CPU 压测**：30-60 秒
- **网络延迟**：60-120 秒
- **磁盘故障**：60 秒以内（避免影响系统正常运行）

### Q4: 如何清理故障？

**A**: 故障会自动在指定持续时间后结束。如需手动清理：

```python
from chaos_mesh_injector import ChaosMeshInjector

injector = ChaosMeshInjector()

# 删除指定故障
injector.delete_chaos(
    namespace="default",
    chaos_name="stress-pod-xxx-xxx",
    chaos_type="stress"
)
```

或使用 kubectl：
```bash
kubectl delete stresschaos <chaos-name> -n <namespace>
kubectl delete networkchaos <chaos-name> -n <namespace>
kubectl delete iochaos <chaos-name> -n <namespace>
```

---

## 进阶功能

### 1. 标签选择器

支持使用标签选择器来选择目标 Pod：

```yaml
target:
  namespace: "default"
  label_selector: "app=nginx,version=v1"
```

### 2. 故障暂停和恢复

支持暂停和恢复故障：

```python
# 暂停故障
kubectl patch stresschaos <chaos-name> -n <namespace> -p '{"spec":{"pause":true}}'

# 恢复故障
kubectl patch stresschaos <chaos-name> -n <namespace> -p '{"spec":{"pause":false}}'
```

### 3. 自定义故障持续时间

支持使用时间单位：`s`（秒）、`m`（分钟）、`h`（小时）

```python
duration="30s"   # 30 秒
duration="5m"    # 5 分钟
duration="1h"    # 1 小时
```

---

## 参考资源

- [Chaos Mesh 官方文档](https://chaos-mesh.org/docs/)
- [Chaos Mesh GitHub](https://github.com/chaos-mesh/chaos-mesh)
- [Kubernetes 官方文档](https://kubernetes.io/docs/)
