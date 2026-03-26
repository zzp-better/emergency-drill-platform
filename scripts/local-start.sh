#!/bin/bash
# =============================================================================
# Emergency Drill Platform - 本地启动脚本（MacBook 远程连接 K8s 集群模式）
# 
# 使用场景：
# - 在 MacBook 本地运行混沌平台
# - 通过 kubeconfig 远程连接虚拟机上的 K8s 集群
# - 从本地执行混沌演练操作
# =============================================================================

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 项目根目录
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# 配置文件
KUBECONFIG_FILE="${KUBECONFIG:-$HOME/.kube/config}"

print_banner() {
    echo -e "${BLUE}"
    echo "╔════════════════════════════════════════════════════════╗"
    echo "║     Emergency Drill Platform - 应急演练自动化平台      ║"
    echo "║           本地运行模式 (远程 K8s 集群)                  ║"
    echo "╚════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查 Python 环境
check_python() {
    log_info "检查 Python 环境..."
    
    if ! command -v python3 &> /dev/null; then
        log_error "未找到 python3，请先安装 Python 3.8+"
        log_info "推荐使用: brew install python@3.10"
        exit 1
    fi
    
    PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
    log_info "Python 版本: $PYTHON_VERSION"
}

# 检查或创建虚拟环境
setup_venv() {
    VENV_DIR="$PROJECT_DIR/venv"
    
    if [[ ! -d "$VENV_DIR" ]]; then
        log_info "创建 Python 虚拟环境..."
        cd "$PROJECT_DIR"
        python3 -m venv venv
    else
        log_info "虚拟环境已存在: $VENV_DIR"
    fi
    
    # 激活虚拟环境
    source "$VENV_DIR/bin/activate"
    
    # 检查依赖是否需要更新
    if [[ requirements.txt -nt "$VENV_DIR/lib" ]] 2>/dev/null; then
        log_info "检测到 requirements.txt 有更新，重新安装依赖..."
        pip install --upgrade pip
        pip install -r requirements.txt
    else
        log_info "检查依赖安装状态..."
        pip install -r requirements.txt -q 2>/dev/null || {
            log_info "安装依赖..."
            pip install -r requirements.txt
        }
    fi
}

# 检查 kubectl 和 kubeconfig
check_k8s_connection() {
    log_info "检查 Kubernetes 连接配置..."
    
    # 检查 kubectl
    if ! command -v kubectl &> /dev/null; then
        log_error "未找到 kubectl，请先安装"
        log_info "推荐使用: brew install kubectl"
        exit 1
    fi
    
    # 检查 kubeconfig
    if [[ ! -f "$KUBECONFIG_FILE" ]]; then
        log_error "未找到 kubeconfig 文件: $KUBECONFIG_FILE"
        log_info "请确保已配置远程 K8s 集群的 kubeconfig"
        exit 1
    fi
    
    log_info "kubeconfig 路径: $KUBECONFIG_FILE"
    
    # 测试连接
    log_info "测试 Kubernetes 集群连接..."
    if kubectl cluster-info &> /dev/null; then
        CLUSTER_VERSION=$(kubectl version --short 2>/dev/null | grep Server | awk '{print $3}')
        log_info "集群连接成功! Server版本: $CLUSTER_VERSION"
        
        # 显示当前上下文
        CURRENT_CONTEXT=$(kubectl config current-context)
        log_info "当前上下文: $CURRENT_CONTEXT"
    else
        log_error "无法连接到 Kubernetes 集群"
        log_warn "请检查:"
        echo "  1. kubeconfig 配置是否正确"
        echo "  2. 远程 K8s 集群是否可达"
        echo "  3. 网络连接是否正常"
        exit 1
    fi
}

# 检查 Chaos Mesh（可选）
check_chaos_mesh() {
    log_info "检查 Chaos Mesh 安装状态..."
    
    if kubectl get namespace chaos-mesh &> /dev/null; then
        if kubectl get pods -n chaos-mesh --no-headers 2>/dev/null | grep -q "Running"; then
            log_info "Chaos Mesh 已安装并运行中"
            return 0
        fi
    fi
    
    log_warn "Chaos Mesh 未安装或未运行"
    log_info "如需使用 Chaos Mesh 功能，请先安装:"
    echo ""
    echo "  # 安装 Chaos Mesh"
    echo "  kubectl apply -f https://mirrors.chaos-mesh.org/v2.6.3/chaos-mesh.yaml"
    echo ""
    return 1
}

# 检查 Prometheus（可选）
check_prometheus() {
    log_info "检查 Prometheus 连接..."
    
    # 从环境变量或配置获取 Prometheus 地址
    PROMETHEUS_URL="${PROMETHEUS_URL:-http://localhost:9090}"
    
    if curl -s --connect-timeout 5 "$PROMETHEUS_URL/-/healthy" &> /dev/null; then
        log_info "Prometheus 连接正常: $PROMETHEUS_URL"
        return 0
    else
        log_warn "无法连接 Prometheus: $PROMETHEUS_URL"
        log_info "如需监控验证功能，请确保 Prometheus 可访问"
        log_info "可通过端口转发访问:"
        echo "  kubectl port-forward -n monitoring svc/prometheus 9090:9090"
        return 1
    fi
}

# 启动 Web UI
start_web_ui() {
    log_info "启动 Web UI..."
    cd "$PROJECT_DIR"
    
    # 设置环境变量
    export KUBECONFIG="$KUBECONFIG_FILE"
    
    # Streamlit 配置
    STREAMLIT_PORT="${STREAMLIT_PORT:-8501}"
    
    log_info "访问地址: http://localhost:$STREAMLIT_PORT"
    log_info "按 Ctrl+C 停止服务"
    echo ""
    
    # 启动 Streamlit
    streamlit run web_ui.py \
        --server.port=$STREAMLIT_PORT \
        --server.address=localhost \
        --server.headless=true \
        --browser.gatherUsageStats=false
}

# 启动命令行模式
start_cli() {
    log_info "启动命令行模式..."
    cd "$PROJECT_DIR"
    
    export KUBECONFIG="$KUBECONFIG_FILE"
    
    echo ""
    echo "可用命令:"
    echo "  python src/chaos_injector.py      # 原生 K8s 故障注入"
    echo "  python src/chaos_mesh_injector.py # Chaos Mesh 故障注入"
    echo "  python src/monitor_checker.py     # Prometheus 监控验证"
    echo "  python examples/quick_start.py    # 快速开始示例"
    echo ""
    
    # 进入交互式 shell
    exec bash
}

# 显示帮助
print_usage() {
    echo "用法: $0 [命令]"
    echo ""
    echo "命令:"
    echo "  web       启动 Web UI (默认)"
    echo "  cli       启动命令行模式"
    echo "  check     仅检查环境配置"
    echo "  help      显示帮助信息"
    echo ""
    echo "环境变量:"
    echo "  KUBECONFIG       kubeconfig 文件路径 (默认: ~/.kube/config)"
    echo "  PROMETHEUS_URL   Prometheus 地址 (默认: http://localhost:9090)"
    echo "  STREAMLIT_PORT   Web UI 端口 (默认: 8501)"
    echo ""
    echo "示例:"
    echo "  $0                          # 启动 Web UI"
    echo "  $0 web                      # 启动 Web UI"
    echo "  $0 cli                      # 启动命令行模式"
    echo "  $0 check                    # 检查环境"
    echo "  KUBECONFIG=~/.kube/remote-config $0  # 使用指定 kubeconfig"
    echo ""
}

# 仅检查环境
check_only() {
    print_banner
    check_python
    setup_venv
    check_k8s_connection
    check_chaos_mesh || true
    check_prometheus || true
    
    echo ""
    log_info "环境检查完成!"
    echo ""
    echo "=============================================="
    echo "  配置摘要"
    echo "=============================================="
    echo "  项目目录:     $PROJECT_DIR"
    echo "  Python:       $(python3 --version 2>&1)"
    echo "  kubeconfig:   $KUBECONFIG_FILE"
    echo "  K8s 上下文:   $(kubectl config current-context 2>/dev/null || echo '未配置')"
    echo "=============================================="
    echo ""
}

# 主函数
main() {
    case "${1:-web}" in
        web)
            print_banner
            check_python
            setup_venv
            check_k8s_connection
            check_chaos_mesh || true
            check_prometheus || true
            echo ""
            start_web_ui
            ;;
        cli)
            print_banner
            check_python
            setup_venv
            check_k8s_connection
            start_cli
            ;;
        check)
            check_only
            ;;
        help|--help|-h)
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
