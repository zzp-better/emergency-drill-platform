#!/bin/bash

# 在 Kubernetes 集群中安装 Chaos Mesh
# 用于混沌演练平台的高级故障注入功能

set -e

echo "=========================================="
echo "安装 Chaos Mesh 到 Kubernetes 集群"
echo "=========================================="

# 1. 添加 Chaos Mesh Helm 仓库
echo ""
echo "1. 添加 Chaos Mesh Helm 仓库"
helm repo add chaos-mesh https://charts.chaos-mesh.org
helm repo update

# 2. 创建命名空间
echo ""
echo "2. 创建 chaos-testing 命名空间"
kubectl create namespace chaos-testing --dry-run=client -o yaml | kubectl apply -f -

# 3. 安装 Chaos Mesh
echo ""
echo "3. 安装 Chaos Mesh (这可能需要几分钟...)"
helm upgrade --install chaos-mesh chaos-mesh/chaos-mesh \
  --namespace chaos-testing \
  --set chaosDaemon.runtime=containerd \
  --set chaosDaemon.socketPath=/run/containerd/containerd.sock \
  --set dashboard.create=true \
  --set dnsServer.create=true \
  --wait

# 4. 验证安装
echo ""
echo "4. 验证 Chaos Mesh 安装状态"
echo ""
kubectl get pods -n chaos-testing

echo ""
echo "=========================================="
echo "Chaos Mesh 安装完成！"
echo "=========================================="
echo ""
echo "Chaos Mesh Dashboard 端口转发（可选）："
echo "  kubectl port-forward -n chaos-testing svc/chaos-mesh-dashboard 2333:2333"
echo ""
echo "然后访问: http://localhost:2333"
echo ""
