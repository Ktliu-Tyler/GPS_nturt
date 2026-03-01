#!/bin/bash
#
# GPS to CAN Sender Service Launcher
# 啟動 GPS to CAN 發送服務
#

set -e

# 配置參數
GPS_PORT="${GPS_PORT:-/dev/ttyUSB0}"
GPS_BAUD="${GPS_BAUD:-115200}"
CAN_INTERFACE="${CAN_INTERFACE:-can1}"
CAN_BITRATE="${CAN_BITRATE:-500000}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="/var/log/gps-can-service"
LOG_FILE="${LOG_DIR}/gps_can_sender.log"

# 建立日誌目錄
mkdir -p "${LOG_DIR}"
chmod 755 "${LOG_DIR}"

# 記錄函數
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "${LOG_FILE}"
}

# 初始化 CAN 介面
init_can_interface() {
    log "正在初始化 CAN 介面: $CAN_INTERFACE @ $CAN_BITRATE bps..."
    
    # 檢查介面是否已存在
    if ! ip link show "${CAN_INTERFACE}" >/dev/null 2>&1; then
        log "建立虛擬 CAN 介面..."
        sudo ip link add dev "${CAN_INTERFACE}" type can || {
            log "❌ 無法建立 CAN 介面"
            exit 1
        }
    fi
    
    # 啟動介面
    sudo ip link set "${CAN_INTERFACE}" up type can bitrate "${CAN_BITRATE}" || {
        log "⚠️  無法設定 CAN 波特率，嘗試啟動現有介面..."
        sudo ip link set "${CAN_INTERFACE}" up || {
            log "❌ 無法啟動 CAN 介面"
            exit 1
        }
    }
    
    # 驗證介面狀態
    if ip link show "${CAN_INTERFACE}" | grep -q "UP"; then
        log "✓ CAN 介面 ${CAN_INTERFACE} 已啟動"
    else
        log "❌ CAN 介面啟動失敗"
        exit 1
    fi
}

# 檢查 GPS 連接
check_gps_connection() {
    log "檢查 GPS 連接: $GPS_PORT..."
    
    if [ ! -c "${GPS_PORT}" ]; then
        log "❌ GPS 設備不存在: $GPS_PORT"
        log "   請檢查 GPS 模組連接"
        log "   可用的設備: $(ls -d /dev/ttyUSB* 2>/dev/null || echo '無')"
        return 1
    fi
    
    log "✓ GPS 設備檢測成功"
    return 0
}

# 主程式
main() {
    log "=========================================="
    log "GPS to CAN 發送服務啟動"
    log "=========================================="
    log "GPS 連接埠: $GPS_PORT"
    log "GPS 波特率: $GPS_BAUD"
    log "CAN 介面: $CAN_INTERFACE"
    log "CAN 波特率: $CAN_BITRATE"
    log "執行檔: $SCRIPT_DIR/gps_can_sender.py"
    log "日誌檔: $LOG_FILE"
    
    # 檢查必要的文件
    if [ ! -f "${SCRIPT_DIR}/gps_can_sender.py" ]; then
        log "❌ 找不到 gps_can_sender.py"
        exit 1
    fi
    
    # 檢查 Python 環境
    if ! command -v python3 &> /dev/null; then
        log "❌ Python3 未安裝"
        exit 1
    fi
    
    # 檢查必要的 Python 套件
    log "檢查 Python 套件..."
    python3 -c "import serial" 2>/dev/null || {
        log "❌ 缺少必要套件: pyserial"
        log "   請執行: pip3 install pyserial python-can"
        exit 1
    }
    
    python3 -c "import can" 2>/dev/null || {
        log "❌ 缺少必要套件: python-can"
        log "   請執行: pip3 install python-can"
        exit 1
    }
    
    # 初始化 CAN
    init_can_interface || exit 1
    
    # 檢查 GPS
    check_gps_connection || exit 1
    
    log "✓ 所有檢查通過，啟動 GPS to CAN 發送器..."
    log "==========================================="
    
    # 啟動發送器
    cd "${SCRIPT_DIR}"
    exec python3 gps_can_sender.py \
        --gps-port="${GPS_PORT}" \
        --gps-baud="${GPS_BAUD}" \
        --can-if="${CAN_INTERFACE}" \
        --can-baud="${CAN_BITRATE}" \
        2>&1 | tee -a "${LOG_FILE}"
}

# 錯誤處理
trap 'log "服務已停止 (退出代碼: $?)"' EXIT

# 啟動主程式
main "$@"
