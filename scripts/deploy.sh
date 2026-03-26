#!/bin/bash
# =============================================================================
# Emergency Drill Platform 部署脚本
# 用于在 Linux 服务器上部署和配置 systemd 服务
# =============================================================================

set -e

# 配置变量
APP_NAME="emergency-drill"
APP_DIR="/emergency-drill-platform"
SERVICE_FILE="emergency-drill.service"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查 root 权限
check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "此脚本需要 root 权限运行"
        log_info "请使用: sudo $0"
        exit 1
    fi
}

# 创建应用目录
create_directories() {
    log_info "创建应用目录: $APP_DIR"
    mkdir -p $APP_DIR
    mkdir -p $APP_DIR/logs
    mkdir -p $APP_DIR/reports
}

# 复制应用文件
copy_files() {
    log_info "复制应用文件..."
    
    # 获取脚本所在目录
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
    
    # 复制必要文件
    cp -r $PROJECT_DIR/src $APP_DIR/
    cp -r $PROJECT_DIR/scenarios $APP_DIR/
    cp -r $PROJECT_DIR/examples $APP_DIR/
    cp $PROJECT_DIR/web_ui.py $APP_DIR/
    cp $PROJECT_DIR/requirements.txt $APP_DIR/
    cp $PROJECT_DIR/README.md $APP_DIR/
    
    log_info "文件复制完成"
}

# 创建 Python 虚拟环境
setup_venv() {
    log_info "创建 Python 虚拟环境..."
    
    cd $APP_DIR
    
    # 检查 Python 3
    if ! command -v python3 &> /dev/null; then
        log_error "未找到 python3，请先安装 Python 3.8+"
        exit 1
    fi
    
    # 创建虚拟环境
    python3 -m venv venv
    
    # 安装依赖
    log_info "安装 Python 依赖..."
    $APP_DIR/venv/bin/pip install --upgrade pip
    $APP_DIR/venv/bin/pip install -r requirements.txt
    
    log_info "Python 环境配置完成"
}



# 安装 systemd 服务
install_service() {
    log_info "安装 systemd 服务..."
    
    # 获取脚本所在目录
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    SERVICE_SRC="$SCRIPT_DIR/$SERVICE_FILE"
    
    if [[ ! -f $SERVICE_SRC ]]; then
        log_error "服务文件不存在: $SERVICE_SRC"
        exit 1
    fi
    
    # 复制服务文件
    cp $SERVICE_SRC /etc/systemd/system/
    
    # 重新加载 systemd
    systemctl daemon-reload
    
    log_info "systemd 服务安装完成"
}

# 启用并启动服务
start_service() {
    log_info "启用并启动服务..."
    
    systemctl enable $APP_NAME
    systemctl start $APP_NAME
    
    # 等待服务启动
    sleep 3
    
    # 检查服务状态
    if systemctl is-active --quiet $APP_NAME; then
        log_info "服务启动成功！"
    else
        log_error "服务启动失败，请检查日志"
        journalctl -u $APP_NAME -n 20 --no-pager
        exit 1
    fi
}

# 显示服务状态
show_status() {
    echo ""
    echo "=============================================="
    log_info "部署完成！"
    echo "=============================================="
    echo ""
    systemctl status $APP_NAME --no-pager
    echo ""
    echo "访问地址: http://localhost:8501"
    echo ""
    echo "常用命令:"
    echo "  启动服务:   sudo systemctl start $APP_NAME"
    echo "  停止服务:   sudo systemctl stop $APP_NAME"
    echo "  重启服务:   sudo systemctl restart $APP_NAME"
    echo "  查看状态:   sudo systemctl status $APP_NAME"
    echo "  查看日志:   sudo journalctl -u $APP_NAME -f"
    echo ""
}

# 主函数
main() {
    echo "=============================================="
    echo "  Emergency Drill Platform 部署脚本"
    echo "=============================================="
    echo ""
    
    check_root
    create_directories
    copy_files
    setup_venv
    install_service
    start_service
    show_status
}

# 运行主函数
main "$@"
