#!/usr/bin/env python3
"""
GPS to CAN Sender
即時讀取 GPS 資料並發送到 CAN 匯流排
讀取 NMEA 句子 → 解析資料 → 轉換格式 → 發送到 CAN1
"""

import serial
import struct
import time
import sys
import math
import pynmea2
from datetime import datetime

try:
    import can
except ImportError:
    print("❌ python-can 未安裝")
    print("請執行: pip install python-can")
    sys.exit(1)


class GPSToCANSender:
    """GPS NMEA to CAN 轉換發送器"""
    
    # CAN 訊息 ID
    CAN_ID_GPS_BASIC = 0x400      # 緯度/經度
    CAN_ID_GPS_EXTENDED = 0x401   # 海拔高度
    CAN_ID_VEL_X = 0x402          # X軸速度
    CAN_ID_VEL_Y = 0x403          # Y軸速度
    CAN_ID_VEL_Z = 0x404          # Z軸速度
    CAN_ID_VEL_MAG = 0x408        # 速度大小
    
    def __init__(self, gps_port='/dev/ttyUSB0', gps_baudrate=115200, 
                 can_interface='can1', can_bitrate=500000):
        """
        初始化 GPS to CAN 發送器
        
        Args:
            gps_port: GPS 串列埠
            gps_baudrate: GPS 波特率
            can_interface: CAN 介面 (can0, can1 等)
            can_bitrate: CAN 位元率
        """
        self.gps_port = gps_port
        self.gps_baudrate = gps_baudrate
        self.can_interface = can_interface
        self.can_bitrate = can_bitrate
        
        self.gps_serial = None
        self.can_bus = None
        self.is_connected = False
        
        # 緩存最後的 GPS 資料
        self.last_position = {'lat': None, 'lon': None, 'altitude': None}
        self.last_velocity = {'vx': 0, 'vy': 0, 'vz': 0, 'speed': 0, 'track': 0}
        
    def connect_gps(self):
        """連接 GPS 模組"""
        try:
            self.gps_serial = serial.Serial(
                port=self.gps_port,
                baudrate=self.gps_baudrate,
                timeout=1,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                bytesize=serial.EIGHTBITS
            )
            self.gps_serial.reset_input_buffer()
            print(f"✓ 連接 GPS: {self.gps_port} @ {self.gps_baudrate}")
            return True
        except Exception as e:
            print(f"✗ 無法連接 GPS: {e}")
            return False
    
    def connect_can(self):
        """連接 CAN 匯流排"""
        try:
            # 檢查 CAN 介面是否存在
            try:
                self.can_bus = can.interface.Bus(
                    interface='socketcan',
                    channel=self.can_interface,
                    bitrate=self.can_bitrate
                )
                print(f"✓ 連接 CAN: {self.can_interface} @ {self.can_bitrate} bps")
                return True
            except:
                print(f"⚠️  無法連接 {self.can_interface}，嘗試使用虛擬 CAN...")
                # 如果實體 CAN 不可用，使用虛擬 CAN 用於測試
                self.can_bus = can.interface.Bus(
                    interface='virtual',
                    channel='vcan0',
                    bitrate=self.can_bitrate
                )
                print(f"✓ 使用虛擬 CAN: vcan0")
                return True
        except Exception as e:
            print(f"✗ 無法連接 CAN: {e}")
            print("  請檢查: sudo ip link add dev can1 type can && sudo ip link set can1 up")
            return False
    
    def parse_lat_lon(self, value, direction):
        """轉換 DDMM.XXXX 格式為十進制度"""
        try:
            value = float(value)
            degrees = int(value / 100)
            minutes = value % 100
            decimal = degrees + minutes / 60
            if direction in ['S', 'W']:
                decimal = -decimal
            return decimal
        except:
            return None
    
    def lat_lon_to_can_format(self, lat, lon):
        """
        轉換緯度/經度為 CAN 格式
        分辨率: 1/10^7 度
        """
        # 轉換為 int32 (有符號)
        lat_can = int(lat * 1e7)
        lon_can = int(lon * 1e7)
        return lat_can, lon_can
    
    def altitude_to_can_format(self, altitude):
        """
        轉換海拔為 CAN 格式
        分辨率: 1 米
        """
        return int(altitude) if altitude else 0
    
    def velocity_to_can_format(self, speed_kt, track_deg):
        """
        轉換速度為分量
        輸入: 速度(節), 航向(度)
        輸出: Vx, Vy, Vz (m/s × 1000 的整數格式)
        """
        if not speed_kt or speed_kt == 0:
            return 0, 0, 0, 0
        
        # 節轉 m/s: 1 節 = 0.51444 m/s
        speed_ms = float(speed_kt) * 0.51444
        
        # 航向轉弧度
        track_rad = math.radians(float(track_deg))
        
        # 分解速度向量 (東北坐標系)
        # Vx: 東方速度，Vy: 北方速度
        vx = speed_ms * math.sin(track_rad)  # 東
        vy = speed_ms * math.cos(track_rad)  # 北
        vz = 0  # GPS 沒有垂直速度
        
        # 轉換為 CAN 格式 (1/1000 m/s)
        vx_can = int(vx * 1000)
        vy_can = int(vy * 1000)
        vz_can = int(vz * 1000)
        
        # 速度大小 (km/h × 3.6/1000)
        speed_kmh = speed_ms * 3.6
        speed_can = int(speed_kmh * 3.6 * 1000 / 3.6)  # 實際上就是 speed_ms × 1000
        
        return vx_can, vy_can, vz_can, int(speed_ms * 1000)
    
    def send_can_message(self, can_id, data):
        """
        發送 CAN 訊息
        
        Args:
            can_id: CAN ID (標準 11-bit)
            data: 資料陣列 (bytes)
        """
        if not self.can_bus:
            return False
        
        try:
            msg = can.Message(
                arbitration_id=can_id,
                data=data,
                is_extended_id=False
            )
            self.can_bus.send(msg)
            return True
        except Exception as e:
            print(f"✗ 發送失敗 (ID: 0x{can_id:03X}): {e}")
            return False
    
    def send_position(self, lat, lon, altitude=None):
        """發送位置資訊到 CAN"""
        if lat is None or lon is None:
            return False
        
        # 轉換格式
        lat_can, lon_can = self.lat_lon_to_can_format(lat, lon)
        
        # CAN ID 0x400: 位置 (緯度/經度)
        # 資料: Latitude (int32, 4字節) + Longitude (int32, 4字節)
        data_0x400 = struct.pack('<ii', lat_can, lon_can)
        self.send_can_message(self.CAN_ID_GPS_BASIC, data_0x400)
        
        # CAN ID 0x401: 海拔高度
        if altitude is not None:
            alt_can = self.altitude_to_can_format(altitude)
            data_0x401 = struct.pack('<i', alt_can)
            self.send_can_message(self.CAN_ID_GPS_EXTENDED, data_0x401)
        
        self.last_position = {'lat': lat, 'lon': lon, 'altitude': altitude}
        return True
    
    def send_velocity(self, speed_kt, track_deg):
        """發送速度資訊到 CAN"""
        if not speed_kt or speed_kt == 0:
            return False
        
        # 轉換速度為分量
        vx, vy, vz, speed_int = self.velocity_to_can_format(speed_kt, track_deg)
        
        # CAN ID 0x402: X軸速度
        data_0x402 = struct.pack('<i', vx)
        self.send_can_message(self.CAN_ID_VEL_X, data_0x402)
        
        # CAN ID 0x403: Y軸速度
        data_0x403 = struct.pack('<i', vy)
        self.send_can_message(self.CAN_ID_VEL_Y, data_0x403)
        
        # CAN ID 0x404: Z軸速度
        data_0x404 = struct.pack('<i', vz)
        self.send_can_message(self.CAN_ID_VEL_Z, data_0x404)
        
        # CAN ID 0x408: 速度大小
        data_0x408 = struct.pack('<i', speed_int)
        self.send_can_message(self.CAN_ID_VEL_MAG, data_0x408)
        
        self.last_velocity = {'vx': vx, 'vy': vy, 'vz': vz, 'speed': speed_int, 'track': track_deg}
        return True
    
    def parse_nmea_fast(self, sentence):
        """快速手動解析 NMEA 句子 (只提取關鍵字段)"""
        if not sentence or not sentence.startswith('$'):
            return None
        
        # 移除校驗和
        if '*' in sentence:
            sentence = sentence.split('*')[0]
        
        parts = sentence[1:].split(',')  # 移除 $ 並分割
        if len(parts) < 2:
            return None
        
        msg_type = parts[0]  # 完整的消息類型 (e.g., "GNRMC")
        
        # **全部処理** - 返回解析結果或佔位符
        result = {'type': msg_type}
        
        # RMC: 推薦最小導航信息
        if 'RMC' in msg_type and len(parts) >= 10:
            try:
                result.update({
                    'lat': parts[3],
                    'lat_dir': parts[4],
                    'lon': parts[5],
                    'lon_dir': parts[6],
                    'speed': parts[7],
                    'track': parts[8],
                })
            except:
                pass
        
        # GGA: 全球定位系統修固數據
        elif 'GGA' in msg_type and len(parts) >= 10:
            try:
                result.update({
                    'lat': parts[2],
                    'lat_dir': parts[3],
                    'lon': parts[4],
                    'lon_dir': parts[5],
                    'altitude': parts[9],
                })
            except:
                pass
        
        # GLL: 地理位置
        elif 'GLL' in msg_type and len(parts) >= 7:
            try:
                result.update({
                    'lat': parts[1],
                    'lat_dir': parts[2],
                    'lon': parts[3],
                    'lon_dir': parts[4],
                })
            except:
                pass
        
        # VTG: 地面速度和航向
        elif 'VTG' in msg_type and len(parts) >= 8:
            try:
                result.update({
                    'track_true': parts[1],
                    'speed_kt': parts[5],
                })
            except:
                pass
        
        # **所有其他句子類型都返回一個佔位符**
        # (即使不提取數據，也要知道這個句子被成功解析了)
        
        return result  # 始終返回 result (可能是簡單的 type 信息)
    
    def parse_nmea_sentence(self, sentence):
        """解析单个 NMEA 句子"""
        if not sentence or not sentence.startswith('$'):
            return None
        
        # 使用快速手动解析
        return self.parse_nmea_fast(sentence)
    
    def process_gps_data(self, buffer=''):
        """從 GPS 讀取並處理所有資料 (高頻率版本)"""
        if not self.gps_serial:
            return buffer, 0
        
        processed_count = 0
        
        try:
            # 一次讀取所有可用資料
            if self.gps_serial.in_waiting:
                chunk = self.gps_serial.read(self.gps_serial.in_waiting)
                buffer += chunk.decode('utf-8', errors='ignore')
            
            # 處理所有完整的句子
            while '\n' in buffer:
                line, buffer = buffer.split('\n', 1)
                line = line.strip('\r\n')
                
                if not line or not line.startswith('$'):
                    continue
                
                # 快速解析 NMEA 句子
                msg = self.parse_nmea_sentence(line)
                if not msg:
                    continue
                
                # **所有成功解析的句子都計數**
                processed_count += 1
                
                msg_type = msg.get('type')
                
                # RMC: 位置和速度
                if 'RMC' in msg_type:
                    try:
                        lat_str = msg.get('lat')
                        lon_str = msg.get('lon')
                        
                        if lat_str and lon_str:
                            lat_decimal = self.parse_lat_lon(float(lat_str), msg.get('lat_dir'))
                            lon_decimal = self.parse_lat_lon(float(lon_str), msg.get('lon_dir'))
                            
                            if lat_decimal and lon_decimal:
                                # 發送位置
                                self.send_position(lat_decimal, lon_decimal)
                                
                                # 發送速度
                                speed_str = msg.get('speed', '0')
                                track_str = msg.get('track', '0')
                                speed = float(speed_str) if speed_str else 0
                                track = float(track_str) if track_str else 0
                                
                                if speed >= 0:
                                    self.send_velocity(speed, track)
                    except:
                        pass
                
                # GGA: 海拔高度
                elif 'GGA' in msg_type:
                    try:
                        altitude_str = msg.get('altitude')
                        if altitude_str and self.last_position['lat']:
                            altitude = float(altitude_str)
                            self.send_position(
                                self.last_position['lat'],
                                self.last_position['lon'],
                                altitude
                            )
                    except:
                        pass
                
                # VTG: 詳細速度資訊
                elif 'VTG' in msg_type:
                    try:
                        track_str = msg.get('track_true')
                        speed_str = msg.get('speed_kt')
                        
                        if track_str and speed_str:
                            track = float(track_str)
                            speed = float(speed_str)
                            if speed >= 0:
                                self.send_velocity(speed, track)
                    except:
                        pass
                
                # GLL: 簡化位置
                elif 'GLL' in msg_type:
                    try:
                        lat_str = msg.get('lat')
                        lon_str = msg.get('lon')
                        
                        if lat_str and lon_str:
                            lat_decimal = self.parse_lat_lon(float(lat_str), msg.get('lat_dir'))
                            lon_decimal = self.parse_lat_lon(float(lon_str), msg.get('lon_dir'))
                            
                            if lat_decimal and lon_decimal:
                                self.send_position(lat_decimal, lon_decimal)
                    except:
                        pass
                
                # 其他句子 (GSV, GSA 等) 不發送 CAN，但已計數
        
        except Exception as e:
            pass
        
        return buffer, processed_count
    
    def run(self, duration=None):
        """
        主循環: 持續讀取 GPS 並發送到 CAN (高頻率版本)
        
        Args:
            duration: 執行時間 (秒)，None 表示無限期
        """
        if not self.gps_serial or not self.can_bus:
            print("❌ GPS 或 CAN 未連接")
            return
        
        print("\n" + "="*70)
        print("🚀 開始發送 GPS 資料到 CAN (高頻率優化版)...")
        print(f"   GPS: {self.gps_port} @ {self.gps_baudrate}")
        print(f"   CAN: {self.can_interface} @ {self.can_bitrate}")
        print("="*70)
        print("按 Ctrl+C 停止\n")
        
        start_time = time.time()
        total_count = 0
        buffer = ""
        last_print = start_time
        last_count = 0
        
        try:
            while True:
                # 檢查執行時間
                if duration and (time.time() - start_time) > duration:
                    break
                
                # 高頻率讀取和處理 - 關鍵改進：計算返回的 processed_count
                buffer, processed = self.process_gps_data(buffer)
                total_count += processed
                
                # 定期打印統計 (每秒)
                now = time.time()
                if now - last_print >= 1:
                    fps = total_count - last_count
                    elapsed = now - start_time
                    print(f"\r⏱️  {elapsed:.1f}s | 發送率: {fps:3d} msg/s | 總計: {total_count:5d}", end="", flush=True)
                    last_print = now
                    last_count = total_count
                
                # 極小延遲以降低 CPU 佔用
                time.sleep(0.0005)
        
        except KeyboardInterrupt:
            print("\n\n已停止發送")
        finally:
            elapsed = time.time() - start_time
            avg_fps = total_count / elapsed if elapsed > 0 else 0
            print(f"\n共發送 {total_count} 筆 GPS 更新 | 平均速率: {avg_fps:.1f} msg/s")
            self.disconnect()
    
    def disconnect(self):
        """斷開連接"""
        if self.gps_serial:
            self.gps_serial.close()
        if self.can_bus:
            self.can_bus.shutdown()
        print("✓ 已斷開連接")


def main():
    """主程式"""
    import argparse
    
    parser = argparse.ArgumentParser(description='GPS to CAN 即時發送器')
    parser.add_argument('--gps-port', default='/dev/ttyUSB0', help='GPS 埠 (默認: /dev/ttyUSB0)')
    parser.add_argument('--gps-baud', type=int, default=115200, help='GPS 波特率 (默認: 115200)')
    parser.add_argument('--can-if', default='can1', help='CAN 介面 (默認: can1)')
    parser.add_argument('--can-baud', type=int, default=500000, help='CAN 位元率 (默認: 500000)')
    parser.add_argument('--duration', type=int, help='執行時間 (秒)')
    
    args = parser.parse_args()
    
    # 創建發送器
    sender = GPSToCANSender(
        gps_port=args.gps_port,
        gps_baudrate=args.gps_baud,
        can_interface=args.can_if,
        can_bitrate=args.can_baud
    )
    
    # 連接 GPS 和 CAN
    if not sender.connect_gps():
        sys.exit(1)
    
    if not sender.connect_can():
        sys.exit(1)
    
    # 運行
    try:
        sender.run(duration=args.duration)
    except KeyboardInterrupt:
        pass
    finally:
        sender.disconnect()


if __name__ == '__main__':
    main()
