#!/bin/bash
# GPS Service 快速部署指南

cat << 'EOF'

╔════════════════════════════════════════════════════════════════╗
║         GPS to CAN Service 快速部署指南                        ║
╚════════════════════════════════════════════════════════════════╝

📁 已創建的檔案：

  ✓ start_gps.sh                 - Service 啟動腳本
  ✓ gps-can-service.service      - systemd service 定義
  ✓ install_service.sh           - 自動安裝腳本
  ✓ SERVICE_README.md            - 詳細說明文檔


🚀 第1步：安裝 Service
═══════════════════════════════════════════════════════════════

  執行安裝命令：

    sudo bash install_service.sh

  這個命令會自動：
    • 檢查系統環境（Python、pip）
    • 安裝 Python 依賴（pyserial、python-can、pynmea2）
    • 設置檔案權限
    • 創建日誌目錄
    • 配置 udev 規則
    • 安裝 systemd service


🎯 第2步：啟動服務
═══════════════════════════════════════════════════════════════

  啟動服務：

    sudo systemctl start gps-can-service

  設置開機自動啟動：

    sudo systemctl enable gps-can-service

  查看服務狀態：

    sudo systemctl status gps-can-service


📊 第3步：監控 GPS 資料和 CAN 消息
═══════════════════════════════════════════════════════════════

  查看實時日誌：

    sudo journalctl -u gps-can-service -f

  或查看檔案日誌：

    tail -f /var/log/gps-can-service/gps_can_sender.log

  監控 CAN 消息：

    candump can1


⚙️ 第4步：配置（可選）
═══════════════════════════════════════════════════════════════

  編輯 service 檔案修改參數：

    sudo nano /etc/systemd/system/gps-can-service.service

  可配置的環境變數：
    • GPS_PORT=/dev/ttyUSB0       (GPS 串列埠)
    • GPS_BAUD=115200             (GPS 波特率)
    • CAN_INTERFACE=can1           (CAN 介面)
    • CAN_BITRATE=500000           (CAN 位元率)

  修改後重新啟動：

    sudo systemctl daemon-reload
    sudo systemctl restart gps-can-service


📋 常用命令速查
═══════════════════════════════════════════════════════════════

  啟動/停止/重啟服務：
    sudo systemctl start   gps-can-service
    sudo systemctl stop    gps-can-service
    sudo systemctl restart gps-can-service

  查看日誌：
    sudo journalctl -u gps-can-service -f
    tail -f /var/log/gps-can-service/gps_can_sender.log

  診斷 GPS 輸出頻率：
    python3 gps_diagnostic.py 15

  監控 CAN 資料：
    candump can1

  數據分析：
    python3 analyze_gps_output.py


🔍 故障排除
═══════════════════════════════════════════════════════════════

  Service 不啟動：
    sudo systemctl status gps-can-service
    sudo journalctl -xe

  GPS 設備找不到：
    ls -l /dev/ttyUSB*
    lsusb

  CAN 介面問題：
    ip link show can1
    sudo ip link set can1 up type can bitrate 500000

  權限問題：
    sudo usermod -aG dialout $USER


📚 更多詳細資訊
═══════════════════════════════════════════════════════════════

  請參考完整文檔：SERVICE_README.md

    cat SERVICE_README.md
    或
    nano SERVICE_README.md


✨ 特性
═══════════════════════════════════════════════════════════════

  ✓ 實時 GPS 到 CAN 轉換
  ✓ ~30 msg/s 高頻率發送
  ✓ 自動故障重啟
  ✓ 開機自動啟動
  ✓ 詳細日誌記錄
  ✓ systemd 完全集成
  ✓ 支持多星座 GPS（GPS、GLONASS、Galileo、BeiDou）


═══════════════════════════════════════════════════════════════

EOF
