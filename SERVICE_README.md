# GPS to CAN Service 部署指南

GPS 到 CAN 匯流排的即時發送服務，支持 systemd 自動管理和日誌記錄。

## 📋 文件說明

| 檔案 | 說明 |
|------|------|
| `gps_can_sender.py` | 主程式：GPS NMEA 解析和 CAN 發送 |
| `start_gps.sh` | 啟動腳本：初始化環境和啟動發送器 |
| `gps-can-service.service` | systemd service 定義檔 |
| `install_service.sh` | 安裝腳本：自動部署 service |
| `gps_diagnostic.py` | 診斷工具：檢測 GPS 輸出頻率 |

## 🚀 快速開始

### 1. 檢查前置條件

```bash
# 確認 Python 和必要套件
python3 --version
pip3 --version

# 確認 GPS 設備已連接
ls -l /dev/ttyUSB*

# 確認 CAN 介面可用
ip link show

# 測試 GPS 輸出
python3 gps_test.py --raw
```

### 2. 安裝 Service

```bash
# 進入 GPS 目錄
cd /home/pi/Desktop/RPI_Desktop/GPS

# 執行安裝腳本 (需要 root 權限)
sudo bash install_service.sh
```

安裝程序會自動：
- ✓ 檢查系統環境（Python、pip）
- ✓ 安裝 Python 依賴（pyserial、python-can、pynmea2）
- ✓ 設置檔案權限
- ✓ 創建日誌目錄
- ✓ 配置 udev 規則
- ✓ 安裝 systemd service

### 3. 啟動服務

```bash
# 手動啟動
sudo systemctl start gps-can-service

# 查看狀態
sudo systemctl status gps-can-service

# 設置開機自動啟動
sudo systemctl enable gps-can-service

# 停止服務
sudo systemctl stop gps-can-service
```

## 📊 監控和調試

### 查看日誌

**選項 1：systemd 日誌**
```bash
# 實時查看
sudo journalctl -u gps-can-service -f

# 查看過去 50 行
sudo journalctl -u gps-can-service -n 50
```

**選項 2：檔案日誌**
```bash
# 實時監控
tail -f /var/log/gps-can-service/gps_can_sender.log

# 查看所有日誌
cat /var/log/gps-can-service/gps_can_sender.log
```

### 監控 CAN 資料

```bash
# 實時顯示 CAN 消息
candump can1

# 統計格式
candump can1 --no-color

# 保存到檔案
candump can1 -l > can_data.log
```

### 診斷 GPS 輸出

```bash
# 測量 GPS 實際輸出頻率
python3 gps_diagnostic.py 15  # 採樣 15 秒
```

## ⚙️ 配置

### 修改環境變數

編輯 service 檔案：
```bash
sudo nano /etc/systemd/system/gps-can-service.service
```

修改以下參數（在 `[Service]` 區塊）：
```ini
Environment="GPS_PORT=/dev/ttyUSB0"      # GPS 串列埠
Environment="GPS_BAUD=115200"            # GPS 波特率
Environment="CAN_INTERFACE=can1"         # CAN 介面
Environment="CAN_BITRATE=500000"         # CAN 波特率
```

保存後重新啟動服務：
```bash
sudo systemctl daemon-reload
sudo systemctl restart gps-can-service
```

### 直接執行 (用於測試)

```bash
# 手動執行啟動腳本
bash start_gps.sh

# 指定參數執行
GPS_PORT=/dev/ttyUSB1 CAN_INTERFACE=can0 bash start_gps.sh

# 直接執行 Python 程式
python3 gps_can_sender.py --gps-port /dev/ttyUSB0 --can-if can1 --duration 60
```

## 📡 CAN 消息格式

| CAN ID | 功能 | 內容 |
|--------|------|------|
| 0x400 | GPS 位置 | 緯度 + 經度 (int32, 分辨率: 1/10^7 度) |
| 0x401 | GPS 海拔 | 高度 (int32, 分辨率: 1 米) |
| 0x402 | X軸速度 | 東向速度 (int32, 分辨率: 1/1000 m/s) |
| 0x403 | Y軸速度 | 北向速度 (int32, 分辨率: 1/1000 m/s) |
| 0x404 | Z軸速度 | 垂直速度 (int32, 分辨率: 1/1000 m/s) |
| 0x408 | 速度大小 | 合成速度 (int32, 分辨率: 1/1000 m/s) |

## 🔧 故障排除

### GPS 設備找不到

```bash
# 檢查連接的 USB 設備
lsusb

# 列出所有序列埠
ls -l /dev/ttyUSB*
ls -l /dev/ttyACM*

# 監控新連接的設備
dmesg -w
# (插入 GPS 模組時查看)
```

### CAN 介面問題

```bash
# 查看 CAN 介面列表
ip link show | grep can

# 啟動 CAN 介面
sudo ip link set can1 up type can bitrate 500000

# 刪除虛擬 CAN（如需重建）
sudo ip link delete can1

# 檢查 CAN 狀態
ip -details link show can1
```

### Python 依賴問題

```bash
# 重新安裝依賴
pip3 install --upgrade pyserial python-can pynmea2

# 檢查已安裝的套件
pip3 list | grep -E 'pyserial|python-can|pynmea2'
```

### 權限問題

```bash
# 給予使用者 CAN 裝置存取權限
sudo usermod -aG dialout $USER

# 重新登入或重啟
exit

# 測試權限
candump can1
```

## 📈 性能指標

| 指標 | 典型值 |
|------|--------|
| GPS 輸出頻率 | ~28.7 Hz |
| CAN 發送速率 | ~30+ msg/s |
| CPU 占用率 | < 5% |
| 記憶體占用 | < 50 MB |

## 🛑 服務生命周期

```
啟動流程：
1. systemd 啟動 gps-can-service.service
2. ExecStart 執行 start_gps.sh
3. start_gps.sh 初始化 CAN 介面
4. start_gps.sh 檢查 GPS 連接
5. start_gps.sh 啟動 gps_can_sender.py
6. Python 程式開始發送 GPS 資料到 CAN

停止流程：
1. systemctl stop gps-can-service 發送 SIGTERM
2. Python 程式優雅關閉
3. 日誌寫入最終訊息
4. 釋放所有資源
```

## 📝 日誌格式

```
[2026-03-01 10:30:45] ==========================================
[2026-03-01 10:30:45] GPS to CAN 發送服務啟動
[2026-03-01 10:30:45] GPS 連接埠: /dev/ttyUSB0
[2026-03-01 10:30:45] CAN 介面: can1
[2026-03-01 10:30:45] ✓ GPS 設備檢測成功
[2026-03-01 10:30:45] ✓ CAN 介面 can1 已啟動
[2026-03-01 10:30:45] ✓ 所有檢查通過，啟動 GPS to CAN 發送器...
[2026-03-01 10:30:46] ======================================================================
[2026-03-01 10:30:46] 🚀 開始發送 GPS 資料到 CAN (高頻率優化版)...
[2026-03-01 10:30:50] ⏱️  5.0s | 發送率:  30 msg/s | 總計:   150
```

## 🤝 故障恢復

Service 配置為故障自動重啟：
```ini
Restart=on-failure      # 故障時重啟
RestartSec=5s          # 等待 5 秒後重啟
```

檢查重啟次數：
```bash
sudo systemctl status gps-can-service
# 會顯示: Restart Count: X
```

## 📞 技術支援

| 問題 | 解決方案 |
|------|---------|
| GPS 無輸出 | 檢查連接、波特率、設備權限 |
| CAN 不工作 | 啟動介面、檢查波特率、驗證配線 |
| Service 不啟動 | 查看日誌、檢查路徑、驗證權限 |
| 高 CPU 占用 | 檢查 GPS 輸出頻率、調整延遲參數 |

## 📚 相關指引

- [NMEA 0183 標準](https://en.wikipedia.org/wiki/NMEA_0183)
- [Socket CAN](https://www.kernel.org/doc/html/latest/networking/can.html)
- [systemd Service 檔案](https://www.freedesktop.org/software/systemd/man/systemd.service.html)
- [python-can 文檔](https://python-can.readthedocs.io/)

---

**最後更新**: 2026-03-01  
**版本**: 1.0
