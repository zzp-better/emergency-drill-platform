#!/bin/bash

# Chaos Mesh Dashboard 永久 Token 配置脚本
# 适用于 Kubernetes 1.24+
#
# 使用方法：
#   chmod +x setup-chaos-token.sh
#   ./setup-chaos-token.sh

set -e

# 配置变量
NAMESPACE="${CHAOS_MESH_NAMESPACE:-chaos-mesh}"
SA_NAME="${CHAOS_MESH_SA:-chaos-mesh-dashboard}"
SECRET_NAME="${SA_NAME}-token"

echo "=========================================="
echo "Chaos Mesh 永久 Token 配置脚本"
echo "=========================================="
echo ""
echo "配置："
echo "  Namespace: $NAMESPACE"
echo "  ServiceAccount: $SA_NAME"
echo "  Secret: $SECRET_NAME"
echo ""

# 1. 创建 ServiceAccount
echo "[1/5] 创建 ServiceAccount..."
kubectl create serviceaccount $SA_NAME -n $NAMESPACE --dry-run=client -o yaml | kubectl apply -f -
echo "✓ ServiceAccount 创建成功"
echo ""

# 2. 创建 ClusterRole
echo "[2/5] 创建 ClusterRole..."
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
echo "✓ ClusterRole 创建成功"
echo ""

# 3. 创建 ClusterRoleBinding
echo "[3/5] 创建 ClusterRoleBinding..."
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
echo "✓ ClusterRoleBinding 创建成功"
echo ""

# 4. 创建 Secret（Kubernetes 1.24+ 推荐方法）
echo "[4/5] 创建 Secret（自动关联 ServiceAccount）..."
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Secret
metadata:
  name: $SECRET_NAME
  namespace: $NAMESPACE
  annotations:
    kubernetes.io/service-account.name: $SA_NAME
type: kubernetes.io/service-account-token
EOF
echo "✓ Secret 创建成功"
echo ""

# 5. 获取 Token
echo "[5/5] 获取永久 Token..."
sleep 2  # 等待 Token 生成
TOKEN=$(kubectl get secret $SECRET_NAME -n $NAMESPACE -o jsonpath='{.data.token}' 2>/dev/null | base64 -d)

if [ -z "$TOKEN" ]; then
    echo "✗ Token 获取失败，请检查 Secret 是否已创建"
    echo ""
    echo "调试信息："
    kubectl get secret $SECRET_NAME -n $NAMESPACE -o yaml
    exit 1
fi

echo "✓ Token 获取成功"
echo ""

# 6. 保存 Token
echo "=========================================="
echo "Chaos Mesh Dashboard Token (永不过期)"
echo "=========================================="
echo ""
echo "$TOKEN"
echo ""
echo "=========================================="
echo ""
echo "保存此 Token，使用它登录 Chaos Mesh Dashboard"
echo ""

# 7. 保存到文件
OUTPUT_FILE="chaos-mesh-token.txt"
echo "$TOKEN" > $OUTPUT_FILE
echo "✓ Token 已保存到: $OUTPUT_FILE"
echo ""

# 8. 显示使用说明
echo "=========================================="
echo "使用说明"
echo "=========================================="
echo ""
echo "1. 启动 Dashboard 端口转发："
echo "   kubectl port-forward -n $NAMESPACE svc/cha-dashboard 2333:2333"
echo ""
echo "2. 浏览器访问："
echo "   http://localhost:2333"
echo ""
echo "3. 选择 \"Token\" 登录方式"
echo "4. 粘贴上面的 Token"
echo ""
echo "=========================================="
echo ""
