#!/bin/bash
# =============================================================================
# Emergency Drill Platform 服务管理脚本
# 提供便捷的服务启动、停止、重启、状态查看等功能
# =============================================================================

APP_NAME="emergency-drill"
SERVICE_NAME="emergency-drill.service"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_banner() {
    echo -e "${BLUE}"
    echo "╔════════════════════════════════════════════╗"
    echo "║   Emergency Drill Platform 服务管理工具    ║"
    echo "╚════════════════════════════════════════════╝"
    echo -e "${NC}"
}

print_usage() {
    echo "用法: $0 {start|stop|restart|status|logs|logs-n|enable|disable|install|uninstall}"
    echo ""
    echo "命令说明:"
    echo "  start     - 启动服务"
    echo "  stop      - 停止服务"
    echo "  restart   - 重启服务"
    echo "  status    - 查看服务状态"
    echo "  logs      - 查看服务日志 (实时)"
    echo "  logs-n N  - 查看最近 N 行日志"
    echo "  enable    - 设置开机自启"
    echo "  disable   - 禁用开机自启"
    echo "  install   - 安装服务"
    echo "  uninstall - 卸载服务"
    echo ""
}

check_root() {
    if [[ $EUID -ne 0 ]]; then
        echo -e "${RED}[错误]${NC} 此操作需要 root 权限"
        echo "请使用: sudo $0 $1"
        exit 1
    fi
}

start_service() {
    check_root "start"
    echo -e "${GREEN}[启动]${NC} 正在启动 $APP_NAME 服务..."
    systemctl start $SERVICE_NAME
    sleep 2
    show_status
}

stop_service() {
    check_root "stop"
    echo -e "${YELLOW}[停止]${NC} 正在停止 $APP_NAME 服务..."
    systemctl stop $SERVICE_NAME
    echo -e "${GREEN}[完成]${NC} 服务已停止"
}

restart_service() {
    check_root "restart"
    echo -e "${YELLOW}[重启]${NC} 正在重启 $APP_NAME 服务..."
    systemctl restart $SERVICE_NAME
    sleep 2
    show_status
}

show_status() {
    echo -e "${BLUE}[状态]${NC} 服务状态:"
    echo ""
    systemctl status $SERVICE_NAME --no-pager
}

show_logs() {
    echo -e "${BLUE}[日志]${NC} 实时日志 (Ctrl+C 退出):"
    echo ""
    journalctl -u $SERVICE_NAME -f
}

show_logs_n() {
    local lines=${1:-100}
    echo -e "${BLUE}[日志]${NC} 最近 $lines 行日志:"
    echo ""
    journalctl -u $SERVICE_NAME -n $lines --no-pager
}

enable_service() {
    check_root "enable"
    echo -e "${GREEN}[启用]${NC} 设置开机自启..."
    systemctl enable $SERVICE_NAME
    echo -e "${GREEN}[完成]${NC} 已设置开机自启"
}

disable_service() {
    check_root "disable"
    echo -e "${YELLOW}[禁用]${NC} 禁用开机自启..."
    systemctl disable $SERVICE_NAME
    echo -e "${GREEN}[完成]${NC} 已禁用开机自启"
}

install_service() {
    check_root "install"
    
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    SERVICE_FILE="$SCRIPT_DIR/emergency-drill.service"
    
    if [[ ! -f $SERVICE_FILE ]]; then
        echo -e "${RED}[错误]${NC} 服务文件不存在: $SERVICE_FILE"
        exit 1
    fi
    
    echo -e "${GREEN}[安装]${NC} 正在安装服务..."
    cp $SERVICE_FILE /etc/systemd/system/
    systemctl daemon-reload
    echo -e "${GREEN}[完成]${NC} 服务已安装"
    echo ""
    echo "使用以下命令启动服务:"
    echo "  sudo $0 start"
}

uninstall_service() {
    check_root "uninstall"
    
    echo -e "${YELLOW}[卸载]${NC} 正在卸载服务..."
    
    # 先停止服务
    systemctl stop $SERVICE_NAME 2>/dev/null || true
    systemctl disable $SERVICE_NAME 2>/dev/null || true
    
    # 删除服务文件
    rm -f /etc/systemd/system/$SERVICE_NAME
    
    # 重新加载 systemd
    systemctl daemon-reload
    
    echo -e "${GREEN}[完成]${NC} 服务已卸载"
}

# 主逻辑
case "$1" in
    start)
        print_banner
        start_service
        ;;
    stop)
        print_banner
        stop_service
        ;;
    restart)
        print_banner
        restart_service
        ;;
    status)
        print_banner
        show_status
        ;;
    logs)
        print_banner
        show_logs
        ;;
    logs-n)
        print_banner
        show_logs_n $2
        ;;
    enable)
        print_banner
        enable_service
        ;;
    disable)
        print_banner
        disable_service
        ;;
    install)
        print_banner
        install_service
        ;;
    uninstall)
        print_banner
        uninstall_service
        ;;
    *)
        print_banner
        print_usage
        exit 1
        ;;
esac

exit 0
