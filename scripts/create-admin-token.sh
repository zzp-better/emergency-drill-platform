#!/bin/bash

# 创建具有集群管理员权限的 Service Account Token
# 用于混沌演练平台的 K8s 集群连接

set -e

echo "=========================================="
echo "创建混沌演练平台管理员 Service Account"
echo "=========================================="

# 定义命名空间和服务账户名称
NAMESPACE="chaos-platform"
SERVICE_ACCOUNT="chaos-platform-admin"
CLUSTER_ROLE_BINDING="chaos-platform-admin-binding"

# 1. 创建命名空间（如果不存在）
echo ""
echo "1. 创建命名空间: $NAMESPACE"
kubectl create namespace $NAMESPACE --dry-run=client -o yaml | kubectl apply -f -

# 2. 创建 Service Account
echo ""
echo "2. 创建 Service Account: $SERVICE_ACCOUNT"
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: ServiceAccount
metadata:
  name: $SERVICE_ACCOUNT
  namespace: $NAMESPACE
EOF

# 3. 创建 ClusterRole（具有集群管理员权限）
echo ""
echo "3. 创建 ClusterRole: chaos-platform-admin-role"
cat <<EOF | kubectl apply -f -
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: chaos-platform-admin-role
rules:
# 完全访问所有核心资源
- apiGroups: [""]
  resources: ["*"]
  verbs: ["*"]
# 完全访问所有 apps 资源
- apiGroups: ["apps"]
  resources: ["*"]
  verbs: ["*"]
# 完全访问 batch 资源
- apiGroups: ["batch"]
  resources: ["*"]
  verbs: ["*"]
# Chaos Mesh 资源权限
- apiGroups: ["chaos-mesh.org"]
  resources: ["*"]
  verbs: ["*"]
# 自定义资源定义
- apiGroups: ["apiextensions.k8s.io"]
  resources: ["customresourcedefinitions"]
  verbs: ["get", "list", "watch"]
# RBAC 权限（用于查看）
- apiGroups: ["rbac.authorization.k8s.io"]
  resources: ["roles", "rolebindings", "clusterroles", "clusterrolebindings"]
  verbs: ["get", "list", "watch"]
# 事件
- apiGroups: [""]
  resources: ["events"]
  verbs: ["get", "list", "watch"]
# 节点
- apiGroups: [""]
  resources: ["nodes"]
  verbs: ["get", "list", "watch"]
EOF

# 4. 创建 ClusterRoleBinding
echo ""
echo "4. 创建 ClusterRoleBinding: $CLUSTER_ROLE_BINDING"
cat <<EOF | kubectl apply -f -
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: $CLUSTER_ROLE_BINDING
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: chaos-platform-admin-role
subjects:
- kind: ServiceAccount
  name: $SERVICE_ACCOUNT
  namespace: $NAMESPACE
EOF

# 5. 创建长期 Token Secret（Kubernetes 1.24+）
echo ""
echo "5. 创建长期 Token Secret"
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Secret
metadata:
  name: $SERVICE_ACCOUNT-token
  namespace: $NAMESPACE
  annotations:
    kubernetes.io/service-account.name: $SERVICE_ACCOUNT
type: kubernetes.io/service-account-token
EOF

# 等待 Token 生成
echo ""
echo "等待 Token 生成..."
sleep 3

# 6. 获取 Token
echo ""
echo "=========================================="
echo "6. 获取 Token 和 CA 证书"
echo "=========================================="

# 获取 Token
TOKEN=$(kubectl get secret $SERVICE_ACCOUNT-token -n $NAMESPACE -o jsonpath='{.data.token}' | base64 -d)

# 获取 CA 证书
CA_CERT=$(kubectl get secret $SERVICE_ACCOUNT-token -n $NAMESPACE -o jsonpath='{.data.ca\.crt}')

# 获取 API Server 地址
API_SERVER=$(kubectl config view --minify -o jsonpath='{.clusters[0].cluster.server}')

echo ""
echo "=========================================="
echo "请在混沌平台配置页面填写以下信息："
echo "=========================================="
echo ""
echo "API Server 地址:"
echo "$API_SERVER"
echo ""
echo "Token (复制以下内容):"
echo "----------------------------------------"
echo "$TOKEN"
echo "----------------------------------------"
echo ""
echo "CA 证书 (复制以下内容，可选):"
echo "----------------------------------------"
echo "$CA_CERT"
echo "----------------------------------------"
echo ""
echo "=========================================="
echo "配置完成！"
echo "=========================================="
