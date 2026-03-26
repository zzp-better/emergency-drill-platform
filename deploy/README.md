# 部署指南

## 前置要求

### Docker Compose 部署
- Docker 20.10+
- Docker Compose 2.0+
- kubectl 配置（用于访问 Kubernetes 集群）

### Kubernetes 部署
- Kubernetes 1.20+
- kubectl 已配置集群访问权限
- 已安装 [Chaos Mesh](https://chaos-mesh.org/docs/production-installation-using-helm/)

---

## 方式一：Docker Compose（推荐用于开发/测试）

### 1. 准备环境变量

```bash
cp .env.example .env
# 根据实际情况修改 .env 中的配置
```

### 2. 启动服务

```bash
cd emergency-drill-platform
docker-compose up -d
```

### 3. 访问服务

- **应急演练平台**: http://localhost:8501
- **Prometheus**: http://localhost:9090
- **Pushgateway**: http://localhost:9091
- **Grafana**: http://localhost:3000 (admin/admin123)

### 4. 停止服务

```bash
docker-compose down
# 删除数据卷
docker-compose down -v
```

---

## 方式二：Kubernetes（推荐用于生产）

### 1. 安装 Chaos Mesh

```bash
helm repo add chaos-mesh https://charts.chaos-mesh.org
helm install chaos-mesh chaos-mesh/chaos-mesh \
  --namespace=chaos-mesh \
  --create-namespace \
  --set chaosDaemon.runtime=containerd \
  --set chaosDaemon.socketPath=/run/containerd/containerd.sock
```

### 2. 构建镜像

```bash
docker build -t emergency-drill-platform:latest .
```

### 3. 部署应用

```bash
# 创建 RBAC 权限
kubectl apply -f deploy/k8s/rbac.yaml

# 部署应用
kubectl apply -f deploy/k8s/deployment.yaml
```

### 4. 访问应用

```bash
# 端口转发
kubectl port-forward -n emergency-drill svc/emergency-drill-platform 8501:8501

# 或创建 Ingress（需要 Ingress Controller）
```

### 5. 查看状态

```bash
kubectl get pods -n emergency-drill
kubectl logs -n emergency-drill -l app=edp -f
```

---

## 监控配置

### Prometheus 数据源

Grafana 已自动配置 Prometheus 数据源，可直接导入仪表板或创建自定义面板。

### 推荐指标查询

```promql
# 演练执行次数
drill_execution_total

# 演练成功率
rate(drill_execution_total{status="success"}[5m]) / rate(drill_execution_total[5m])

# 故障注入延迟
drill_injection_duration_seconds
```

---

## 故障排查

### 应用无法启动

```bash
# 检查日志
docker-compose logs app
# 或
kubectl logs -n emergency-drill -l app=edp
```

### 无法连接 Kubernetes

确保 kubeconfig 路径正确：
- Docker Compose: 检查 `.env` 中的 `KUBECONFIG_PATH`
- Kubernetes: 应用 Pod 会使用 ServiceAccount 自动认证

### Chaos Mesh 注入失败

检查 RBAC 权限：
```bash
kubectl auth can-i create podchaos.chaos-mesh.org \
  --as=system:serviceaccount:emergency-drill:edp-sa
```

---

## 生产环境建议

1. **持久化存储**: 修改 PVC 使用 StorageClass，确保数据持久化
2. **资源限制**: 根据实际负载调整 `resources.limits`
3. **高可用**: 增加 `replicas` 并配置 Pod 反亲和性
4. **安全加固**:
   - 修改 Grafana 默认密码
   - 启用 TLS/HTTPS
   - 配置网络策略限制 Pod 间通信
5. **监控告警**: 配置 Prometheus AlertManager
