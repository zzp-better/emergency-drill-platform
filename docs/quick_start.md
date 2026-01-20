# 快速入门指南

欢迎使用应急演练自动化平台！本指南将帮助你在 10 分钟内完成第一次故障注入。

## 第一步：安装 Python 依赖

```bash
# 进入项目目录
cd emergency-drill-platform

# 安装依赖
pip install -r requirements.txt
```

## 第二步：验证 Kubernetes 连接

确保你的 kubectl 已经配置好：

```bash
# 检查 Kubernetes 连接
kubectl cluster-info

# 查看当前的 Pod
kubectl get pods --all-namespaces
```

## 第三步：部署测试应用（如果还没有）

如果你的集群还没有测试应用，可以快速部署一个 nginx：

```bash
# 创建一个 nginx Deployment
kubectl create deployment nginx-demo --image=nginx:alpine

# 扩展到 3 个副本
kubectl scale deployment nginx-demo --replicas=3

# 查看 Pod 状态
kubectl get pods -l app=nginx-demo
```

等待 Pod 变为 Running 状态。

## 第四步：运行第一个故障注入

### 方式 1：使用交互式示例（推荐新手）

```bash
# 运行交互式示例
python examples/quick_start.py
```

按照提示操作：
1. 选择 "1" 列出所有 Pod
2. 记下一个 Pod 的名称（比如 `nginx-demo-xxxx-xxxx`）
3. 选择 "2" 删除这个 Pod
4. 观察 Pod 是否自动恢复

### 方式 2：直接使用 Python 代码

```python
from src.chaos_injector import ChaosInjector

# 初始化故障注入器
injector = ChaosInjector()

# 删除一个 Pod（替换为你的 Pod 名称）
result = injector.delete_pod(
    namespace="default",
    pod_name="nginx-demo-xxxx-xxxx"
)

# 查看结果
print(f"执行状态: {result['success']}")
print(f"恢复时间: {result['recovery_time']} 秒")
```

## 第五步：观察结果

故障注入后，你会看到：

✅ Pod 被删除
✅ Kubernetes 自动创建新 Pod
✅ 新 Pod 在约 20-30 秒内恢复到 Running 状态
✅ 系统记录了完整的恢复时间

## 下一步

恭喜！你已经完成了第一次故障注入。

接下来可以：

1. **集成监控验证**：验证 Prometheus 告警是否触发
2. **使用配置文件**：通过 YAML 配置场景参数
3. **生成演练报告**：自动生成 Markdown 格式的报告
4. **集成 Chaos Mesh**：实现更多故障类型（CPU 压测、网络延迟等）

查看 [scenarios/pod_crash.yaml](../scenarios/pod_crash.yaml) 了解配置文件格式。

## 常见问题

### 1. 提示 "Kubernetes API 错误"

**原因**：kubectl 配置不正确或集群未运行

**解决**：
```bash
# 检查 kubeconfig 文件
echo $KUBECONFIG

# 验证集群连接
kubectl cluster-info
```

### 2. Pod 没有自动恢复

**原因**：Pod 不是由 Deployment/ReplicaSet 管理的

**解决**：只删除由 Deployment 创建的 Pod，这样 Kubernetes 才会自动重建

### 3. 找不到 Python 模块

**原因**：依赖未安装

**解决**：
```bash
pip install -r requirements.txt
```

## 技术支持

遇到问题？

- 查看 [README.md](../README.md)
- 提交 GitHub Issue
- 查看示例代码 [examples/quick_start.py](../examples/quick_start.py)
