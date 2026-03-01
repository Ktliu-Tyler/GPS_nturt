#!/bin/bash
#
# GPS to CAN Service 部署安裝腳本
# Deploy GPS to CAN Service
#

set -e

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 訊息函數
info() { echo -e "${GREEN}ℹ️  $*${NC}"; }
warn() { echo -e "${YELLOW}⚠️  $*${NC}"; }
error() { echo -e "${RED}❌ $*${NC}"; }
success() { echo -e "${GREEN}✓ $*${NC}"; }

# 檢查權限
check_root() {
    if [[ $EUID -ne 0 ]]; then
        error "此腳本必須以 root 身份執行"
        echo "請執行: sudo $0"
        exit 1
    fi
}

# 檢查系統環境
check_system() {
    info "檢查系統環境..."
    
    # 檢查 Python
    if ! command -v python3 &> /dev/null; then
        error "Python3 未安裝"
        echo "請執行: sudo apt-get install python3 python3-pip"
        exit 1
    fi
    success "Python3 已安裝"
    
    # 檢查 pip
    if ! command -v pip3 &> /dev/null; then
        error "pip3 未安裝"
        echo "請執行: sudo apt-get install python3-pip"
        exit 1
    fi
    success "pip3 已安裝"
}

# 安裝 Python 依賴
install_dependencies() {
    info "安裝 Python 依賴..."
    
    pip3 install -q pyserial python-can pynmea2 2>/dev/null && \
        success "Python 依賴已安裝" || \
        warn "某些依賴安裝可能失敗"
}

# 取得安裝目錄
get_install_dir() {
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    info "安裝目錄: $SCRIPT_DIR"
}

# 設定檔案權限
setup_permissions() {
    info "設定檔案權限..."
    
    chmod +x "${SCRIPT_DIR}/start_gps.sh"
    chmod +x "${SCRIPT_DIR}/gps_can_sender.py"
    
    success "檔案權限已設定"
}

# 複製 Service 檔案
install_service() {
    info "安裝 systemd service..."
    
    SERVICE_FILE="/etc/systemd/system/gps-can-service.service"
    
    if [ ! -f "${SCRIPT_DIR}/gps-can-service.service" ]; then
        error "找不到 service 檔案: ${SCRIPT_DIR}/gps-can-service.service"
        exit 1
    fi
    
    cp "${SCRIPT_DIR}/gps-can-service.service" "${SERVICE_FILE}"
    
    # 更新路徑 (如果需要)
    sed -i "s|/home/pi/Desktop/RPI_Desktop/GPS|${SCRIPT_DIR}|g" "${SERVICE_FILE}"
    
    # 重新載入 systemd
    systemctl daemon-reload
    
    success "Service 已安裝到: $SERVICE_FILE"
}

# 建立日誌目錄
setup_logging() {
    info "設定日誌目錄..."
    
    LOG_DIR="/var/log/gps-can-service"
    mkdir -p "${LOG_DIR}"
    chmod 755 "${LOG_DIR}"
    
    success "日誌目錄已建立: $LOG_DIR"
}

# 配置 udev 規則 (給予一般使用者 GPS 裝置的存取權)
setup_udev_rules() {
    info "設定 udev 規則..."
    
    UDEV_RULE="/etc/udev/rules.d/99-usb-gps.rules"
    
    # 為所有 USB 序列埠建立規則
    cat > "${UDEV_RULE}" << 'EOF'
# USB to Serial Adapter GPS
SUBSYSTEMS=="usb", ATTRS{idVendor}=="1546", ATTRS{idProduct}=="01a7", MODE="0666"
SUBSYSTEMS=="usb", ATTRS{idVendor}=="10c4", ATTRS{idProduct}=="ea60", MODE="0666"
# Generic USB Serial
SUBSYSTEMS=="usb-serial", DRIVER=="ch341-uart", MODE="0666"
# ftdi_sio
SUBSYSTEMS=="usb", ATTRS{idVendor}=="0403", ATTRS{idProduct}=="6001", MODE="0666"
EOF
    
    # 重新載入 udev 規則
    udevadm control --reload-rules
    udevadm trigger
    
    success "udev 規則已設定"
}

# 顯示使用說明
show_usage() {
    echo ""
    echo "========================================"
    echo "GPS to CAN Service 部署完成！"
    echo "========================================"
    echo ""
    echo "📋 常用命令："
    echo ""
    echo "  啟動服務："
    echo "    sudo systemctl start gps-can-service"
    echo ""
    echo "  停止服務："
    echo "    sudo systemctl stop gps-can-service"
    echo ""
    echo "  查看狀態："
    echo "    sudo systemctl status gps-can-service"
    echo ""
    echo "  查看日誌："
    echo "    sudo journalctl -u gps-can-service -f"
    echo "    或"
    echo "    tail -f /var/log/gps-can-service/gps_can_sender.log"
    echo ""
    echo "  設定開機自動啟動："
    echo "    sudo systemctl enable gps-can-service"
    echo ""
    echo "  取消開機自動啟動："
    echo "    sudo systemctl disable gps-can-service"
    echo ""
    echo "  監控 CAN 資料："
    echo "    candump can1"
    echo ""
    echo "📝 設定環境變數 (修改 service 檔案)："
    echo "  GPS_PORT=/dev/ttyUSB0 (預設)"
    echo "  GPS_BAUD=115200 (預設)"
    echo "  CAN_INTERFACE=can1 (預設)"
    echo "  CAN_BITRATE=500000 (預設)"
    echo ""
    echo "編輯: sudo nano /etc/systemd/system/gps-can-service.service"
    echo "修改完成後執行: sudo systemctl daemon-reload"
    echo ""
    echo "========================================"
}

# 主程式
main() {
    echo "========================================"
    echo "GPS to CAN Service 安裝程式"
    echo "========================================"
    echo ""
    
    check_root
    check_system
    get_install_dir
    setup_permissions
    install_dependencies
    setup_logging
    setup_udev_rules
    install_service
    
    echo ""
    success "安裝完成！"
    show_usage
}

# 執行
main "$@"
