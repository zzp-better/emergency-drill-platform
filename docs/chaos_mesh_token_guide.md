# Chaos Mesh Token 配置指南

## 问题描述

Chaos Mesh Dashboard 默认使用临时 Token，Token 会过期，需要频繁重新登录。

## 解决方案

### 方法 1：使用 ServiceAccount Token（推荐 - Kubernetes 1.24+）

这是 Kubernetes 1.24+ 推荐的简洁方法，通过 Secret 注解自动关联 ServiceAccount。

#### 步骤 1：创建 ServiceAccount

```bash
# 创建 ServiceAccount
kubectl create serviceaccount chaos-mesh-dashboard -n chaos-mesh

# 创建 ClusterRole
cat <<EOF | kubectl apply -f -
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: chaos-mesh-dashboard
rules:
- apiGroups: ["*"]
  resources: ["*"]
  verbs: ["*"]
EOF

# 创建 ClusterRoleBinding
cat <<EOF | kubectl apply -f -
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: chaos-mesh-dashboard
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: chaos-mesh-dashboard
subjects:
- kind: ServiceAccount
  name: chaos-mesh-dashboard
  namespace: chaos-mesh
EOF
```

#### 步骤 2：获取永久 Token

```bash
# 获取 ServiceAccount 的 Secret 名称
SECRET_NAME=$(kubectl get sa chaos-mesh-dashboard -n chaos-mesh -o jsonpath='{.secrets[0].name}')

# 获取 Token
TOKEN=$(kubectl get secret $SECRET_NAME -n chaos-mesh -o jsonpath='{.data.token}' | base64 -d)

echo "Token: $TOKEN"
```

#### 步骤 3：配置 Chaos Mesh 使用永久 Token

编辑 Chaos Mesh Dashboard 的 Deployment：

```bash
kubectl edit deployment chaos-dashboard -n chaos-mesh
```

在环境变量中添加：

```yaml
env:
- name: GIN_MODE
  value: release
- name: SECURITY_MODE
  value: true
- name: AUTH_MODE
  value: rbac
- name: RBAC_MODE
  value: token
```

或者使用 Secret 存储 Token：

```bash
# 创建 Secret 存储 Token
kubectl create secret generic chaos-dashboard-token \
  --from-literal=token=$TOKEN \
  -n chaos-mesh

# 更新 Deployment 使用 Secret
kubectl set env deployment/cha-dashboard \
  --from=secret/cha-dashboard-token \
  -n chaos-mesh
```

### 方法 2：使用 OIDC/SSO 集成（企业环境）

如果您的企业有 OIDC 或 SSO 系统，可以集成 Chaos Mesh。

#### 步骤 1：配置 OIDC

编辑 Chaos Mesh 的 values.yaml（如果是 Helm 安装）：

```yaml
dashboard:
  securityMode: true
  authMode: oidc
  oidc:
    issuer: https://your-oidc-provider.com
    clientId: chaos-mesh-dashboard
    clientSecret: your-client-secret
    scopes: openid profile email
    redirectURL: https://chaos-mesh.example.com/api/callback
```

#### 步骤 2：重新部署 Chaos Mesh

```bash
helm upgrade chaos-mesh chaos-mesh/chaos-mesh \
  --namespace chaos-mesh \
  -f values.yaml
```

### 方法 3：禁用认证（仅限测试环境）

⚠️ **警告**：仅适用于测试环境，生产环境不建议禁用认证。

#### 步骤 1：编辑 Chaos Mesh 配置

```bash
kubectl edit deployment chaos-dashboard -n chaos-mesh
```

#### 步骤 2：禁用认证

修改环境变量：

```yaml
env:
- name: SECURITY_MODE
  value: "false"
```

或者删除认证相关的环境变量。

#### 步骤 3：重启 Pod

```bash
kubectl rollout restart deployment chaos-dashboard -n chaos-mesh
```

### 方法 4：延长 Token 有效期

如果不想使用永久 Token，可以延长临时 Token 的有效期。

#### 步骤 1：修改 Chaos Mesh 配置

编辑 Chaos Mesh Manager 的 Deployment：

```bash
kubectl edit deployment chaos-controller-manager -n chaos-mesh
```

#### 步骤 2：添加环境变量

```yaml
env:
- name: TOKEN_EXPIRATION
  value: "720h"  # 30天
```

支持的值：
- `24h` - 1天
- `168h` - 7天
- `720h` - 30天
- `8760h` - 1年

## 验证配置

### 检查 Token 是否永久

```bash
# 查看 Dashboard 的环境变量
kubectl exec -n chaos-mesh deployment/cha-dashboard -- env | grep -i auth

# 查看 Token Secret
kubectl get secret chaos-dashboard-token -n chaos-mesh -o yaml
```

### 测试登录

使用获取的 Token 登录 Chaos Mesh Dashboard：

```bash
# 方式 1：使用 kubectl port-forward
kubectl port-forward -n chaos-mesh svc/cha-dashboard 2333:2333

# 浏览器访问：http://localhost:2333
# 使用 Token 登录
```

## 常用命令

```bash
# 查看 Chaos Mesh 所有组件
kubectl get all -n chaos-mesh

# 查看 Dashboard 日志
kubectl logs -n chaos-mesh -l app.kubernetes.io/component=dashboard -f

# 查看 Controller 日志
kubectl logs -n chaos-mesh -l app.kubernetes.io/component=controller-manager -f

# 重启 Dashboard
kubectl rollout restart deployment chaos-dashboard -n chaos-mesh

# 查看 RBAC 配置
kubectl get clusterrole,clusterrolebinding -n chaos-mesh | grep chaos-mesh
```

## 完整示例：配置永久 Token（推荐方法）

```bash
#!/bin/bash

NAMESPACE="chaos-mesh"
SA_NAME="cha-mesh-dashboard"

# 1. 创建 ServiceAccount
kubectl create serviceaccount $SA_NAME -n $NAMESPACE

# 2. 创建 ClusterRole
cat <<EOF | kubectl apply -f -
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: chaos-mesh-dashboard
rules:
- apiGroups: ["*"]
  resources: ["*"]
  verbs: ["*"]
EOF

# 3. 创建 ClusterRoleBinding
cat <<EOF | kubectl apply -f -
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: chaos-mesh-dashboard
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: chaos-mesh-dashboard
subjects:
- kind: ServiceAccount
  name: $SA_NAME
  namespace: $NAMESPACE
EOF

# 4. 创建 Secret（Kubernetes 1.24+ 推荐方法）
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Secret
metadata:
  name: ${SA_NAME}-token
  namespace: $NAMESPACE
  annotations:
    kubernetes.io/service-account.name: $SA_NAME
type: kubernetes.io/service-account-token
EOF

# 5. 获取 Token
TOKEN=$(kubectl get secret ${SA_NAME}-token -n $NAMESPACE -o jsonpath='{.data.token}' | base64 -d)

# 6. 保存 Token
echo "=========================================="
echo "Chaos Mesh Dashboard Token (永不过期)"
echo "=========================================="
echo ""
echo "$TOKEN"
echo ""
echo "=========================================="
echo "保存此 Token，使用它登录 Chaos Mesh Dashboard"
echo "=========================================="

# 7. 可选：保存到文件
echo "$TOKEN" > chaos-mesh-token.txt
echo "Token 已保存到: chaos-mesh-token.txt"
```

## 一键执行脚本

将上面的脚本保存为 `setup-chaos-token.sh`，然后执行：

```bash
chmod +x setup-chaos-token.sh
./setup-chaos-token.sh
```

## 使用 Token 登录

```bash
# 方式 1：使用 kubectl port-forward
kubectl port-forward -n chaos-mesh svc/cha-dashboard 2333:2333

# 浏览器访问：http://localhost:2333
# 选择 "Token" 登录方式
# 粘贴上面获取的 Token
```

## 注意事项

1. **安全性**：永久 Token 有安全风险，请妥善保管
2. **权限**：ServiceAccount 应只授予必要的权限
3. **轮换**：定期更换 Token 以提高安全性
4. **备份**：保存 Token 到安全的位置（如密码管理器）

## 参考文档

- [Chaos Mesh 官方文档 - Security](https://chaos-mesh.org/docs/security/)
- [Chaos Mesh 官方文档 - RBAC](https://chaos-mesh.org/docs/rbac/)
- [Kubernetes RBAC 文档](https://kubernetes.io/docs/reference/access-authn-authz/rbac/)
