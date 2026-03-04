# Chaos Mesh 故障注入验证指南

## 问题：故障注入成功但 Pod 没有反应？

如果故障注入显示成功，但目标 Pod 没有反应，可能是以下原因：

## 常见原因和解决方案

### 1. Pod 没有安装 Chaos Mesh Sidecar

**症状**：验证结果显示 "有 Chaos Sidecar: False"

**原因**：Chaos Mesh 需要在 Pod 中注入 sidecar 容器才能执行故障。

**解决方案**：

#### 方法 1：使用注解启用 Chaos Mesh（推荐）

为 Pod 或其所在的 Namespace 添加注解：

```bash
# 为单个 Pod 添加注解
kubectl annotate pod <pod-name> chaos-mesh.org/chaos-inject="true" -n <namespace>

# 为整个 Namespace 添加注解（所有 Pod 都会被注入）
kubectl annotate namespace <namespace> chaos-mesh.org/chaos-inject="true"
```

#### 方法 2：使用 Selector 选择器

在创建故障时使用标签选择器而不是 Pod 名称：

```python
# 使用标签选择器
spec = {
    "mode": "one",
    "selector": {
        "namespaces": [namespace],
        "labelSelectors": {
            "app": "nginx"  # 使用标签选择 Pod
        }
    },
    ...
}
```

#### 方法 3：重新部署 Pod

添加注解后，需要重新部署 Pod：

```bash
# 删除旧 Pod（如果是 Deployment 管理的）
kubectl delete pod <pod-name> -n <namespace>

# 或者重新部署 Deployment
kubectl rollout restart deployment <deployment-name> -n <namespace>
```

### 2. Chaos Mesh 未正确安装

**症状**：无法列出 Chaos Mesh 资源

**检查方法**：

```bash
# 检查 Chaos Mesh CRD 是否已安装
kubectl get crd | grep chaos-mesh.org

# 检查 Chaos Mesh 控制器是否运行
kubectl get pods -n chaos-mesh

# 检查 Chaos Mesh 的 webhook
kubectl get validatingwebhookconfigurations | grep chaos-mesh
```

**解决方案**：参考 [Chaos Mesh 官方安装文档](https://chaos-mesh.org/docs/installation)

### 3. Pod 不在正确的 Namespace 中

**症状**：验证结果显示 "Pod 不存在"

**检查方法**：

```bash
# 列出所有 Pod
kubectl get pods -A

# 查找目标 Pod
kubectl get pods -n <namespace>
```

**解决方案**：确保 Pod 名称和 Namespace 正确

### 4. 实验状态异常

**症状**：验证结果显示 "实验状态异常"

**检查方法**：

```bash
# 查看故障详情
kubectl describe stresschaos <chaos-name> -n <namespace>

# 查看 Chaos Mesh 控制器日志
kubectl logs -n chaos-mesh -l app.kubernetes.io/component=controller-manager
```

**常见错误**：

- `Failed to inject chaos`: sidecar 注入失败
- `Pod not found`: 目标 Pod 不存在
- `Namespace not allowed`: Namespace 没有启用 Chaos Mesh

### 5. 资源限制

**症状**：Pod 没有足够的 CPU/内存资源

**检查方法**：

```bash
# 查看 Pod 的资源限制
kubectl describe pod <pod-name> -n <namespace> | grep -A 10 "Limits"
```

**解决方案**：确保 Pod 有足够的资源来承受压测

## 验证步骤

### 使用本平台的验证功能

运行 `quick_test.py` 时，会自动进行验证：

```bash
python examples/quick_test.py
```

选择 "3. CPU 压测"，输入参数后，会自动显示验证结果。

### 手动验证

#### 1. 检查 Chaos Mesh 资源

```bash
# 列出所有 StressChaos
kubectl get stresschaos -n <namespace>

# 查看故障详情
kubectl describe stresschaos <chaos-name> -n <namespace>

# 查看 YAML 配置
kubectl get stresschaos <chaos-name> -n <namespace> -o yaml
```

#### 2. 检查 Pod 状态

```bash
# 查看 Pod 状态
kubectl get pod <pod-name> -n <namespace>

# 查看 Pod 详情
kubectl describe pod <pod-name> -n <namespace>

# 查看 Pod 日志
kubectl logs <pod-name> -n <namespace>

# 查看 Chaos Mesh sidecar 日志
kubectl logs <pod-name> -n <namespace> -c chaos-daemon
```

#### 3. 检查 Pod 的 Sidecar

```bash
# 查看 Pod 的容器列表
kubectl get pod <pod-name> -n <namespace> -o jsonpath='{.spec.containers[*].name}'

# 应该看到类似：
# nginx chaos-daemon
```

#### 4. 监控资源使用

```bash
# 实时查看 CPU 使用
kubectl top pod <pod-name> -n <namespace> --containers

# 查看内存使用
kubectl top pod <pod-name> -n <namespace>
```

## 完整示例

### 1. 为 Namespace 启用 Chaos Mesh

```bash
# 添加注解
kubectl annotate namespace default chaos-mesh.org/chaos-inject="true"

# 重新部署应用
kubectl rollout restart deployment nginx -n default
```

### 2. 运行故障注入

```bash
python examples/quick_test.py

# 选择 3. CPU 压测
# 输入参数：
#   命名空间: default
#   Pod 名称: nginx-xxx-xxx
#   CPU 核心数: 2
#   内存大小: 100Mi
#   持续时间: 60s
```

### 3. 验证故障注入

```bash
# 查看 Chaos 资源
kubectl get stresschaos -n default

# 查看 Pod 资源使用
kubectl top pod nginx-xxx-xxx -n default --containers

# 应该看到 CPU 使用率上升
```

### 4. 查看 Pod 日志

```bash
# 查看应用日志
kubectl logs nginx-xxx-xxx -n default -f

# 查看 Chaos sidecar 日志
kubectl logs nginx-xxx-xxx -n default -c chaos-daemon -f
```

## 常用命令

```bash
# 列出所有 Chaos Mesh 资源
kubectl get stresschaos -A
kubectl get networkchaos -A
kubectl get iochaos -A
kubectl get podchaos -A

# 删除故障
kubectl delete stresschaos <chaos-name> -n <namespace>

# 查看故障状态
kubectl get stresschaos <chaos-name> -n <namespace> -o yaml

# 查看 Chaos Mesh 控制器日志
kubectl logs -n chaos-mesh -l app.kubernetes.io/component=controller-manager -f

# 查看 Chaos Mesh DaemonSet
kubectl get ds -n chaos-mesh
```

## 故障排查清单

- [ ] Chaos Mesh 已正确安装
- [ ] Chaos Mesh 控制器 Pod 正在运行
- [ ] 目标 Namespace 已添加 `chaos-mesh.org/chaos-inject="true"` 注解
- [ ] 目标 Pod 已重新部署（添加注解后）
- [ ] Pod 中包含 `chaos-daemon` sidecar 容器
- [ ] Chaos Mesh 资源已创建
- [ ] 故障状态为 "Running"
- [ ] Pod 有足够的 CPU/内存资源
- [ ] 没有网络策略阻止 sidecar 通信

## 参考文档

- [Chaos Mesh 官方文档](https://chaos-mesh.org/docs/)
- [Chaos Mesh 安装指南](https://chaos-mesh.org/docs/installation)
- [StressChaos 使用说明](https://chaos-mesh.org/docs/chaos-mesh/stresschaos/)
