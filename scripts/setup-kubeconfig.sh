#!/bin/bash
# =============================================================================
# Emergency Drill Platform - 远程 K8s 集群配置脚本
# 
# 用于配置 MacBook 连接远程虚拟机 K8s 集群
# =============================================================================

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_banner() {
    echo -e "${BLUE}"
    echo "╔════════════════════════════════════════════════════════╗"
    echo "║        远程 Kubernetes 集群配置工具                    ║"
    echo "╚════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

print_usage() {
    echo "用法: $0 [命令]"
    echo ""
    echo "命令:"
    echo "  setup <remote-host>     从远程服务器复制 kubeconfig"
    echo "  list                    列出所有可用的 kubeconfig"
    echo "  switch <context>        切换 K8s 上下文"
    echo "  test                    测试集群连接"
    echo "  port-forward            设置 Prometheus 端口转发"
    echo "  help                    显示帮助"
    echo ""
    echo "示例:"
    echo "  $0 setup root@192.168.1.100"
    echo "  $0 list"
    echo "  $0 switch kubernetes-admin@kubernetes"
    echo "  $0 test"
    echo ""
}

# 从远程服务器复制 kubeconfig
setup_kubeconfig() {
    local remote_host="$1"
    
    if [[ -z "$remote_host" ]]; then
        log_error "请指定远程主机地址"
        echo "用法: $0 setup <user@host>"
        echo "示例: $0 setup root@192.168.1.100"
        exit 1
    fi
    
    log_info "从远程服务器复制 kubeconfig: $remote_host"
    
    # 创建备份目录
    KUBE_DIR="$HOME/.kube"
    BACKUP_DIR="$KUBE_DIR/backup"
    mkdir -p "$BACKUP_DIR"
    
    # 备份现有配置
    if [[ -f "$KUBE_DIR/config" ]]; then
        BACKUP_FILE="$BACKUP_DIR/config.$(date +%Y%m%d_%H%M%S)"
        cp "$KUBE_DIR/config" "$BACKUP_FILE"
        log_info "已备份现有配置到: $BACKUP_FILE"
    fi
    
    # 从远程服务器复制 kubeconfig
    log_info "复制 /etc/kubernetes/admin.conf ..."
    ssh "$remote_host" "cat /etc/kubernetes/admin.conf" > "$KUBE_DIR/config.remote" 2>/dev/null || {
        log_error "无法从远程服务器复制 kubeconfig"
        log_info "请确保:"
        echo "  1. 可以 SSH 连接到远程服务器"
        echo "  2. 远程服务器是 K8s master 节点"
        echo "  3. 有权限读取 /etc/kubernetes/admin.conf"
        exit 1
    }
    
    # 获取远程服务器 IP
    REMOTE_IP=$(echo "$remote_host" | grep -oE '[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+' || echo "")
    if [[ -z "$REMOTE_IP" ]]; then
        REMOTE_IP=$(ssh "$remote_host" "hostname -I | awk '{print \$1}'" 2>/dev/null)
    fi
    
    log_info "远程服务器 IP: $REMOTE_IP"
    
    # 替换 server 地址（如果需要）
    if [[ -n "$REMOTE_IP" ]]; then
        # 检查是否需要替换
        if grep -q "server: https://127.0.0.1" "$KUBE_DIR/config.remote" || \
           grep -q "server: https://localhost" "$KUBE_DIR/config.remote"; then
            log_info "替换 server 地址为远程 IP..."
            sed -i.tmp "s/server: https:\/\/127.0.0.1/server: https:\/\/$REMOTE_IP/g" "$KUBE_DIR/config.remote"
            sed -i.tmp "s/server: https:\/\/localhost/server: https:\/\/$REMOTE_IP/g" "$KUBE_DIR/config.remote"
            rm -f "$KUBE_DIR/config.remote.tmp"
        fi
    fi
    
    # 合并或替换配置
    if [[ -f "$KUBE_DIR/config" ]]; then
        echo ""
        echo "发现现有 kubeconfig，请选择:"
        echo "  1) 替换现有配置"
        echo "  2) 合并到现有配置"
        echo "  3) 取消"
        echo ""
        read -p "请选择 [1-3]: " choice
        
        case $choice in
            1)
                cp "$KUBE_DIR/config.remote" "$KUBE_DIR/config"
                log_info "已替换 kubeconfig"
                ;;
            2)
                # 合并配置
                KUBECONFIG="$KUBE_DIR/config:$KUBE_DIR/config.remote" kubectl config view --flatten > "$KUBE_DIR/config.merged"
                mv "$KUBE_DIR/config.merged" "$KUBE_DIR/config"
                log_info "已合并 kubeconfig"
                ;;
            3)
                log_info "已取消"
                rm -f "$KUBE_DIR/config.remote"
                exit 0
                ;;
            *)
                log_error "无效选择"
                rm -f "$KUBE_DIR/config.remote"
                exit 1
                ;;
        esac
    else
        mv "$KUBE_DIR/config.remote" "$KUBE_DIR/config"
        log_info "已创建 kubeconfig"
    fi
    
    # 设置权限
    chmod 600 "$KUBE_DIR/config"
    
    # 测试连接
    log_info "测试集群连接..."
    if kubectl cluster-info &> /dev/null; then
        log_info "集群连接成功!"
        kubectl cluster-info
    else
        log_error "集群连接失败，请检查配置"
    fi
    
    # 清理临时文件
    rm -f "$KUBE_DIR/config.remote"
}

# 列出所有上下文
list_contexts() {
    log_info "可用的 Kubernetes 上下文:"
    echo ""
    kubectl config get-contexts
    echo ""
    log_info "当前上下文: $(kubectl config current-context)"
}

# 切换上下文
switch_context() {
    local context="$1"
    
    if [[ -z "$context" ]]; then
        log_error "请指定上下文名称"
        echo "可用的上下文:"
        kubectl config get-contexts -o name
        exit 1
    fi
    
    log_info "切换到上下文: $context"
    kubectl config use-context "$context"
    log_info "当前上下文: $(kubectl config current-context)"
}

# 测试集群连接
test_connection() {
    log_info "测试 Kubernetes 集群连接..."
    echo ""
    
    # 检查 kubectl
    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl 未安装"
        log_info "安装: brew install kubectl"
        exit 1
    fi
    
    log_info "kubectl 版本: $(kubectl version --client --short 2>/dev/null || kubectl version --client)"
    
    # 检查 kubeconfig
    KUBECONFIG_FILE="${KUBECONFIG:-$HOME/.kube/config}"
    if [[ ! -f "$KUBECONFIG_FILE" ]]; then
        log_error "kubeconfig 不存在: $KUBECONFIG_FILE"
        exit 1
    fi
    log_info "kubeconfig: $KUBECONFIG_FILE"
    
    # 测试连接
    echo ""
    if kubectl cluster-info &> /dev/null; then
        log_info "✅ 集群连接成功"
        echo ""
        kubectl cluster-info
        echo ""
        log_info "集群版本: $(kubectl version --short 2>/dev/null | grep Server)"
        log_info "当前上下文: $(kubectl config current-context)"
        echo ""
        log_info "节点状态:"
        kubectl get nodes -o wide
        echo ""
        log_info "命名空间:"
        kubectl get namespaces
    else
        log_error "❌ 集群连接失败"
        echo ""
        log_info "排查步骤:"
        echo "  1. 检查 kubeconfig 配置是否正确"
        echo "  2. 确认远程 K8s 集群是否运行"
        echo "  3. 检查网络连通性 (ping, telnet)"
        echo "  4. 确认防火墙是否放行 6443 端口"
        exit 1
    fi
}

# 设置端口转发
setup_port_forward() {
    log_info "设置 Prometheus 端口转发..."
    echo ""
    
    # 检查 Prometheus 命名空间
    PROM_NS=""
    for ns in monitoring prometheus kube-system; do
        if kubectl get namespace "$ns" &> /dev/null; then
            if kubectl get svc -n "$ns" 2>/dev/null | grep -qi prometheus; then
                PROM_NS="$ns"
                break
            fi
        fi
    done
    
    if [[ -z "$PROM_NS" ]]; then
        log_warn "未找到 Prometheus 服务"
        log_info "请手动指定命名空间和服务:"
        echo "  kubectl port-forward -n <namespace> svc/<service-name> 9090:9090"
        exit 1
    fi
    
    log_info "在命名空间 $PROM_NS 中找到 Prometheus"
    
    # 获取服务名称
    PROM_SVC=$(kubectl get svc -n "$PROM_NS" -o jsonpath='{.items[?(@.metadata.name.contains("prometheus"))].metadata.name}' 2>/dev/null | head -1)
    
    if [[ -z "$PROM_SVC" ]]; then
        PROM_SVC="prometheus"
    fi
    
    log_info "启动端口转发: svc/$PROM_SVC (namespace: $PROM_NS)"
    log_info "Prometheus 地址: http://localhost:9090"
    log_info "按 Ctrl+C 停止"
    echo ""
    
    kubectl port-forward -n "$PROM_NS" "svc/$PROM_SVC" 9090:9090
}

# 主函数
main() {
    case "${1:-help}" in
        setup)
            print_banner
            setup_kubeconfig "$2"
            ;;
        list)
            print_banner
            list_contexts
            ;;
        switch)
            switch_context "$2"
            ;;
        test)
            print_banner
            test_connection
            ;;
        port-forward)
            setup_port_forward
            ;;
        help|--help|-h)
            print_banner
            print_usage
            ;;
        *)
            log_error "未知命令: $1"
            print_usage
            exit 1
            ;;
    esac
}

main "$@"
