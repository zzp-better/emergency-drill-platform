# 部署指南 (DEPLOYMENT.md)

## 目录

- [系统要求](#系统要求)
- [部署架构](#部署架构)
- [快速部署](#快速部署)
- [详细部署步骤](#详细部署步骤)
- [配置说明](#配置说明)
- [验证部署](#验证部署)
- [常见问题](#常见问题)
- [卸载指南](#卸载指南)

---

## 系统要求

### 硬件要求

| 组件 | 最低配置 | 推荐配置 |
|------|---------|---------|
| CPU | 2 核 | 4 核+ |
| 内存 | 4 GB | 8 GB+ |
| 磁盘 | 20 GB | 50 GB+ |

### 软件要求

#### 必需组件

- **Kubernetes 集群**: v1.20+
  - 本地开发: Minikube / Kind / K3s
  - 生产环境: 标准 Kubernetes 集群
- **Python**: 3.8+
- **kubectl**: 已配置并可访问集群
- **pip**: Python 包管理器

#### 可选组件

- **Chaos Mesh**: v2.6+ (用于高级故障场景)
- **Helm**: v3.0+ (用于 Chaos Mesh 安装)
- **Docker**: 用于容器化部署
- **Prometheus**: 用于监控验证功能
- **Grafana**: 用于可视化监控

---

## 部署架构

```
┌─────────────────────────────────────────────────────────┐
│                   用户访问层                              │
│  ┌──────────────┐         ┌──────────────┐              │
│  │  Web UI      │         │  CLI 工具     │              │
│  │ (Streamlit)  │         │  (Python)     │              │
│  └──────────────┘         └──────────────┘              │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│              应急演练自动化平台核心                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │ 故障注入模块  │  │ 监控验证模块  │  │ 报告生成模块  │  │
│  │ChaosInjector │  │MonitorChecker│  │ReportGenerator│  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
└─────────────────────────────────────────────────────────┘
           │                    │
           ▼                    ▼
┌──────────────────┐   ┌──────────────────┐
│  Kubernetes API  │   │  Prometheus API  │
│  ┌────────────┐  │   │  ┌────────────┐  │
│  │ Pod 管理   │  │   │  │ 告警查询   │  │
│  │ 资源监控   │  │   │  │ 指标查询   │  │
│  └────────────┘  │   │  └────────────┘  │
└──────────────────┘   └──────────────────┘
           │
           ▼
┌──────────────────┐
│   Chaos Mesh     │
│  (可选高级功能)   │
│  ┌────────────┐  │
│  │ CPU 压测   │  │
│  │ 网络故障   │  │
│  │ 磁盘故障   │  │
│  └────────────┘  │
└──────────────────┘
```

---

## 快速部署

### 方式一：本地开发环境（推荐新手）

```bash
# 1. 克隆项目
git clone <repository-url>
cd emergency-drill-platform

# 2. 安装 Python 依赖
pip install -r requirements.txt

# 3. 配置 Kubernetes 访问
export KUBECONFIG=~/.kube/config

# 4. 启动 Web UI
streamlit run web_ui.py

# 5. 访问 http://localhost:8501
```

### 方式二：Docker 容器部署（推荐生产）

```bash
# 1. 构建镜像
docker build -t emergency-drill-platform:latest .

# 2. 运行容器
docker run -d \
  --name edap \
  -p 8501:8501 \
  -v ~/.kube/config:/root/.kube/config:ro \
  -e PROMETHEUS_URL=http://prometheus:9090 \
  emergency-drill-platform:latest

# 3. 访问 http://localhost:8501
```

### 方式三：Kubernetes 部署（推荐集群环境）

```bash
# 1. 创建命名空间
kubectl create namespace emergency-drill

# 2. 部署应用
kubectl apply -f k8s/deployment.yaml -n emergency-drill

# 3. 暴露服务
kubectl port-forward -n emergency-drill svc/edap-web 8501:8501

# 4. 访问 http://localhost:8501
```

---

## 详细部署步骤

### 步骤 1: 准备 Kubernetes 集群

#### 选项 A: 使用 Minikube（本地开发）

```bash
# 安装 Minikube
curl -LO https://storage.googleapis.com/minikube/releases/latest/minikube-linux-amd64
sudo install minikube-linux-amd64 /usr/local/bin/minikube

# 启动集群
minikube start --cpus=4 --memory=8192 --driver=docker

# 验证集群
kubectl cluster-info
kubectl get nodes
```

#### 选项 B: 使用 Kind（本地开发）

```bash
# 安装 Kind
curl -Lo ./kind https://kind.sigs.k8s.io/dl/v0.20.0/kind-linux-amd64
chmod +x ./kind
sudo mv ./kind /usr/local/bin/kind

# 创建集群
kind create cluster --name emergency-drill

# 验证集群
kubectl cluster-info --context kind-emergency-drill
```

#### 选项 C: 使用现有 Kubernetes 集群

```bash
# 配置 kubectl 访问
export KUBECONFIG=/path/to/your/kubeconfig

# 验证访问
kubectl get nodes
kubectl get namespaces
```

### 步骤 2: 安装 Prometheus（监控验证功能）

```bash
# 创建 monitoring 命名空间
kubectl create namespace monitoring

# 部署 Prometheus
kubectl apply -f 文档/yaml文档/prometheus-rbac.yaml
kubectl apply -f 文档/yaml文档/prometheus-configmap.yaml
kubectl apply -f 文档/yaml文档/prometheus-statefulset.yaml
kubectl apply -f 文档/yaml文档/prometheus-service.yaml

# 验证 Prometheus 部署
kubectl get pods -n monitoring
kubectl get svc -n monitoring

# 访问 Prometheus UI（端口转发）
kubectl port-forward -n monitoring svc/prometheus 9090:9090
# 浏览器访问: http://localhost:9090
```

### 步骤 3: 安装 Chaos Mesh（可选，高级故障场景）

```bash
# 添加 Helm 仓库
helm repo add chaos-mesh https://charts.chaos-mesh.org
helm repo update

# 创建命名空间
kubectl create namespace chaos-mesh

# 安装 Chaos Mesh
helm install chaos-mesh chaos-mesh/chaos-mesh \
  --namespace chaos-mesh \
  --version 2.6.1 \
  --set chaosDaemon.runtime=containerd \
  --set chaosDaemon.socketPath=/run/containerd/containerd.sock

# 验证安装
kubectl get pods -n chaos-mesh

# 等待所有 Pod 运行
kubectl wait --for=condition=Ready pods --all -n chaos-mesh --timeout=300s

# 诊断 Chaos Mesh（如果遇到问题）
python scripts/diagnose_chaos_mesh.py
```

### 步骤 4: 部署测试应用

```bash
# 部署 Nginx 测试应用
kubectl apply -f 文档/yaml文档/nginx-test-deployment.yaml

# 验证部署
kubectl get pods -l app=nginx
kubectl get svc nginx

# 测试访问
kubectl port-forward svc/nginx 8080:80
curl http://localhost:8080
```

### 步骤 5: 安装应急演练平台

#### 方式 A: Python 本地运行

```bash
# 1. 进入项目目录
cd emergency-drill-platform

# 2. 创建虚拟环境（推荐）
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate  # Windows

# 3. 安装依赖
pip install --upgrade pip
pip install -r requirements.txt

# 4. 配置环境变量
export PROMETHEUS_URL=http://localhost:9090
export KUBECONFIG=~/.kube/config

# 5. 运行测试
python run_tests.py

# 6. 启动 Web UI
streamlit run web_ui.py --server.port 8501 --server.address 0.0.0.0
```

#### 方式 B: Docker 容器运行

```bash
# 1. 创建 Dockerfile（如果不存在）
cat > Dockerfile <<'EOF'
FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY . .

# 暴露端口
EXPOSE 8501

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8501/_stcore/health || exit 1

# 启动应用
CMD ["streamlit", "run", "web_ui.py", "--server.port=8501", "--server.address=0.0.0.0"]
EOF

# 2. 构建镜像
docker build -t emergency-drill-platform:v1.0.0 .

# 3. 运行容器
docker run -d \
  --name edap \
  --network host \
  -v ~/.kube/config:/root/.kube/config:ro \
  -e PROMETHEUS_URL=http://localhost:9090 \
  emergency-drill-platform:v1.0.0

# 4. 查看日志
docker logs -f edap

# 5. 访问应用
# 浏览器访问: http://localhost:8501
```

#### 方式 C: Kubernetes 部署

```bash
# 1. 创建 Kubernetes 部署文件
mkdir -p k8s

cat > k8s/deployment.yaml <<'EOF'
apiVersion: v1
kind: Namespace
metadata:
  name: emergency-drill
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: edap-sa
  namespace: emergency-drill
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: edap-role
rules:
- apiGroups: [""]
  resources: ["pods", "pods/log", "services", "namespaces"]
  verbs: ["get", "list", "watch", "delete"]
- apiGroups: ["apps"]
  resources: ["deployments", "replicasets", "statefulsets"]
  verbs: ["get", "list", "watch"]
- apiGroups: ["chaos-mesh.org"]
  resources: ["*"]
  verbs: ["get", "list", "create", "delete", "patch", "update"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: edap-rolebinding
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: edap-role
subjects:
- kind: ServiceAccount
  name: edap-sa
  namespace: emergency-drill
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: edap-config
  namespace: emergency-drill
data:
  PROMETHEUS_URL: "http://prometheus.monitoring.svc.cluster.local:9090"
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: edap-web
  namespace: emergency-drill
  labels:
    app: edap
spec:
  replicas: 1
  selector:
    matchLabels:
      app: edap
  template:
    metadata:
      labels:
        app: edap
    spec:
      serviceAccountName: edap-sa
      containers:
      - name: web
        image: emergency-drill-platform:v1.0.0
        imagePullPolicy: IfNotPresent
        ports:
        - containerPort: 8501
          name: http
        env:
        - name: PROMETHEUS_URL
          valueFrom:
            configMapKeyRef:
              name: edap-config
              key: PROMETHEUS_URL
        resources:
          requests:
            cpu: 100m
            memory: 256Mi
          limits:
            cpu: 500m
            memory: 512Mi
        livenessProbe:
          httpGet:
            path: /_stcore/health
            port: 8501
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /_stcore/health
            port: 8501
          initialDelaySeconds: 10
          periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: edap-web
  namespace: emergency-drill
spec:
  type: ClusterIP
  selector:
    app: edap
  ports:
  - port: 8501
    targetPort: 8501
    name: http
EOF

# 2. 部署到 Kubernetes
kubectl apply -f k8s/deployment.yaml

# 3. 验证部署
kubectl get pods -n emergency-drill
kubectl get svc -n emergency-drill

# 4. 访问应用（端口转发）
kubectl port-forward -n emergency-drill svc/edap-web 8501:8501

# 5. 或者创建 Ingress（生产环境）
cat > k8s/ingress.yaml <<'EOF'
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: edap-ingress
  namespace: emergency-drill
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /
spec:
  ingressClassName: nginx
  rules:
  - host: edap.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: edap-web
            port:
              number: 8501
EOF

kubectl apply -f k8s/ingress.yaml
```

---

## 配置说明

### 环境变量配置

| 变量名 | 说明 | 默认值 | 示例 |
|--------|------|--------|------|
| `PROMETHEUS_URL` | Prometheus 服务地址 | `http://localhost:9090` | `http://prometheus.monitoring:9090` |
| `KUBECONFIG` | Kubernetes 配置文件路径 | `~/.kube/config` | `/etc/kubernetes/admin.conf` |
| `LOG_LEVEL` | 日志级别 | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR` |

### Prometheus 配置

确保 Prometheus 已配置以下告警规则（参考 [prometheus-rules.yaml](文档/yaml文档/prometheus-rules.yaml)）:

```yaml
groups:
- name: pod_alerts
  rules:
  - alert: PodCrashLooping
    expr: rate(kube_pod_container_status_restarts_total[5m]) > 0
    for: 1m
    labels:
      severity: critical
    annotations:
      summary: "Pod {{ $labels.pod }} is crash looping"
```

### Chaos Mesh 配置

如果使用 Chaos Mesh，需要确保：

1. Chaos Mesh 已正确安装
2. 目标命名空间已启用 Chaos Mesh 注入
3. ServiceAccount 有足够的权限

```bash
# 为命名空间启用 Chaos Mesh
kubectl label namespace default chaos-mesh.org/inject=enabled
```

---

## 验证部署

### 1. 验证 Kubernetes 连接

```bash
# 运行快速测试
python examples/quick_test.py
```

### 2. 验证 Prometheus 连接

```bash
# 测试 Prometheus API
curl http://localhost:9090/api/v1/query?query=up

# 或使用 Python 脚本
python src/monitor_checker.py
```

### 3. 验证故障注入功能

```bash
# 运行完整演练测试
python examples/complete_drill.py
```

### 4. 验证 Web UI

```bash
# 启动 Web UI
streamlit run web_ui.py

# 访问 http://localhost:8501
# 检查以下功能：
# - 首页显示正常
# - 故障注入器可以初始化
# - 监控验证器可以连接 Prometheus
# - 可以加载故障场景配置
```

### 5. 运行自动化测试

```bash
# 运行单元测试
python run_tests.py

# 运行集成测试
pytest tests/integration/ -v

# 查看测试覆盖率
pytest --cov=src --cov-report=html
```

---

## 常见问题

### Q1: Kubernetes 连接失败

**问题**: `Unable to connect to Kubernetes cluster`

**解决方案**:
```bash
# 检查 kubeconfig
kubectl cluster-info

# 检查权限
kubectl auth can-i get pods --all-namespaces

# 设置正确的 KUBECONFIG
export KUBECONFIG=~/.kube/config
```

### Q2: Prometheus 连接超时

**问题**: `Connection timeout when querying Prometheus`

**解决方案**:
```bash
# 检查 Prometheus 是否运行
kubectl get pods -n monitoring

# 端口转发
kubectl port-forward -n monitoring svc/prometheus 9090:9090

# 测试连接
curl http://localhost:9090/api/v1/query?query=up
```

### Q3: Chaos Mesh 故障注入失败

**问题**: `Chaos Mesh injection failed`

**解决方案**:
```bash
# 检查 Chaos Mesh 状态
kubectl get pods -n chaos-mesh

# 运行诊断脚本
python scripts/diagnose_chaos_mesh.py

# 查看日志
kubectl logs -n chaos-mesh -l app.kubernetes.io/component=controller-manager
```

### Q4: Web UI 无法访问

**问题**: `Cannot access Web UI at localhost:8501`

**解决方案**:
```bash
# 检查进程
ps aux | grep streamlit

# 检查端口占用
netstat -tuln | grep 8501

# 使用不同端口
streamlit run web_ui.py --server.port 8502

# 检查防火墙
sudo ufw allow 8501/tcp
```

### Q5: 权限不足

**问题**: `Forbidden: User cannot delete pods`

**解决方案**:
```bash
# 检查当前权限
kubectl auth can-i delete pods --all-namespaces

# 创建 ServiceAccount 和 RBAC（参考 k8s/deployment.yaml）
kubectl apply -f k8s/deployment.yaml

# 使用 ServiceAccount 运行
kubectl run edap --serviceaccount=edap-sa --image=emergency-drill-platform:v1.0.0
```

---

## 卸载指南

### 卸载应急演练平台

```bash
# 停止 Web UI
pkill -f streamlit

# 删除 Kubernetes 部署
kubectl delete namespace emergency-drill

# 删除 Docker 容器
docker stop edap
docker rm edap
docker rmi emergency-drill-platform:v1.0.0

# 删除虚拟环境
deactivate
rm -rf venv
```

### 卸载 Chaos Mesh

```bash
# 使用 Helm 卸载
helm uninstall chaos-mesh -n chaos-mesh

# 删除 CRD
kubectl delete crd $(kubectl get crd | grep chaos-mesh.org | awk '{print $1}')

# 删除命名空间
kubectl delete namespace chaos-mesh
```

### 卸载 Prometheus

```bash
# 删除 Prometheus 部署
kubectl delete -f 文档/yaml文档/prometheus-statefulset.yaml
kubectl delete -f 文档/yaml文档/prometheus-service.yaml
kubectl delete -f 文档/yaml文档/prometheus-configmap.yaml
kubectl delete -f 文档/yaml文档/prometheus-rbac.yaml

# 删除命名空间
kubectl delete namespace monitoring
```

### 清理测试数据

```bash
# 删除演练报告
rm -rf reports/

# 删除日志文件
rm -rf logs/

# 删除缓存
rm -rf __pycache__
rm -rf .pytest_cache
```

---

## 下一步

- 阅读 [ARCHITECTURE.md](ARCHITECTURE.md) 了解系统架构
- 阅读 [API.md](API.md) 了解 API 使用方法
- 查看 [examples/](examples/) 目录获取更多示例
- 访问 [docs/](docs/) 目录查看详细文档

---

## 技术支持

- **GitHub Issues**: 提交问题和建议
- **文档**: 查看 docs/ 目录
- **示例代码**: 参考 examples/ 目录

---

**最后更新**: 2026-01-29
**版本**: v1.0.0
