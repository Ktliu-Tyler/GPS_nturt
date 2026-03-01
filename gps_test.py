#!/usr/bin/env python3
"""
LC29H GPS Module Reader
讀取連接在 /dev/ttyUSB0 的 LC29H GPS 模組
"""

import serial
import time
import pynmea2
import sys
from datetime import datetime

class LC29HGPSReader:
    # LC29H 常見波特率
    COMMON_BAUDRATES = [115200, 9600, 38400, 57600, 4800]
    
    def __init__(self, port='/dev/ttyUSB0', baudrate=115200, timeout=1, debug=False):
        """
        初始化 GPS 模組讀取器
        
        Args:
            port: 串列埠名稱 (預設: /dev/ttyUSB0)
            baudrate: 波特率 (LC29H 預設: 115200)
            timeout: 讀取超時時間 (秒)
            debug: 是否顯示除錯訊息
        """
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.ser = None
        self.is_connected = False
        self.debug = debug
        
    def connect(self):
        """連接到 GPS 模組"""
        try:
            self.ser = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=self.timeout,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                bytesize=serial.EIGHTBITS
            )
            self.is_connected = True
            print(f"✓ 成功連接到 {self.port} (波特率: {self.baudrate})")
            # 清空緩衝區
            self.ser.reset_input_buffer()
            return True
        except serial.SerialException as e:
            print(f"✗ 無法連接到 {self.port}: {e}")
            print("  請檢查：")
            print("  1. USB 線是否正確連接")
            print("  2. 執行 'ls /dev/ttyUSB*' 檢查裝置")
            print("  3. 使用者權限 (可能需要 sudo)")
            return False
    
    def auto_detect_baudrate(self):
        """自動偵測正確的波特率"""
        print("正在自動偵測波特率...")
        
        for baud in self.COMMON_BAUDRATES:
            try:
                print(f"  嘗試 {baud}...", end=" ")
                self.ser = serial.Serial(
                    port=self.port,
                    baudrate=baud,
                    timeout=2,
                    parity=serial.PARITY_NONE,
                    stopbits=serial.STOPBITS_ONE,
                    bytesize=serial.EIGHTBITS
                )
                self.ser.reset_input_buffer()
                time.sleep(0.5)
                
                # 嘗試讀取資料
                raw_data = b''
                start = time.time()
                while (time.time() - start) < 2:
                    if self.ser.in_waiting:
                        raw_data += self.ser.read(self.ser.in_waiting)
                        if b'$' in raw_data and (b'\r\n' in raw_data or b'\n' in raw_data):
                            # 檢查是否有有效的 NMEA 句子
                            try:
                                text = raw_data.decode('utf-8', errors='ignore')
                                if any(x in text for x in ['$GP', '$GN', '$GL', '$GA', '$BD']):
                                    print(f"✓ 偵測到有效資料!")
                                    self.baudrate = baud
                                    self.is_connected = True
                                    print(f"✓ 正確波特率: {baud}")
                                    return True
                            except:
                                pass
                    time.sleep(0.1)
                
                self.ser.close()
                print("無資料")
            except Exception as e:
                print(f"錯誤: {e}")
        
        print("✗ 無法偵測到正確的波特率")
        return False
    
    def disconnect(self):
        """斷開連接"""
        if self.ser and self.is_connected:
            self.ser.close()
            self.is_connected = False
            print("✓ 已斷開連接")
    
    def read_gps_data(self, max_attempts=10):
        """
        讀取一筆 GPS 資料
        
        Args:
            max_attempts: 最多嘗試讀取次數
            
        Returns:
            dict: 包含 GPS 資料的字典，如果失敗則返回 None
        """
        if not self.is_connected:
            return None
        
        attempts = 0
        while attempts < max_attempts:
            try:
                # 使用 readline 直接讀取，不依賴 in_waiting
                line = self.ser.readline()
                
                if line:
                    if self.debug:
                        print(f"[DEBUG] 原始資料: {line}")
                    
                    try:
                        line = line.decode('utf-8', errors='ignore').strip()
                    except:
                        attempts += 1
                        continue
                    
                    if line.startswith('$'):
                        try:
                            # 解析 NMEA 句子
                            msg = pynmea2.parse(line)
                            
                            # 根據句子類型提取資料
                            gps_data = {
                                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                'sentence_type': msg.sentence_type,
                                'raw': line
                            }
                            
                            # GGA 句子 (定位資訊)
                            if msg.sentence_type == 'GGA':
                                gps_data.update({
                                    'latitude': float(msg.lat) if msg.lat else None,
                                    'longitude': float(msg.lon) if msg.lon else None,
                                    'altitude': float(msg.altitude) if msg.altitude else None,
                                    'fix_quality': int(msg.fix_qual) if msg.fix_qual else None,
                                    'num_satellites': int(msg.num_sats) if msg.num_sats else None,
                                    'hdop': float(msg.horizontal_dil) if msg.horizontal_dil else None,
                            })
                            
                            # RMC 句子 (推薦最小導航訊息)
                            elif msg.sentence_type == 'RMC':
                                gps_data.update({
                                    'latitude': float(msg.lat) if msg.lat else None,
                                    'longitude': float(msg.lon) if msg.lon else None,
                                    'speed_knots': float(msg.spd_over_grnd) if msg.spd_over_grnd else None,
                                    'track_angle': float(msg.true_track) if msg.true_track else None,
                                    'date': str(msg.datestamp) if msg.datestamp else None,
                                    'status': msg.status  # 'A'=有效, 'V'=無效
                            })
                            
                            # GSA 句子 (衛星活動訊息)
                            elif msg.sentence_type == 'GSA':
                                gps_data.update({
                                    'fix_type': int(msg.fix_type) if msg.fix_type else None,  # 1=未定位, 2=2D, 3=3D
                                    'used_satellites': msg.sv_id if hasattr(msg, 'sv_id') else None,
                            })
                            
                            return gps_data
                        except pynmea2.ParseError:
                            # 無法解析此句子，繼續讀取下一個
                            pass
            except Exception as e:
                print(f"讀取錯誤: {e}")
            
            attempts += 1
            time.sleep(0.1)
        
        return None
    
    def print_gps_data(self, data):
        """格式化並列印 GPS 資料"""
        if not data:
            return
        
        print(f"\n時間: {data['timestamp']}")
        print(f"句子類型: {data['sentence_type']}")
        
        if 'latitude' in data and data['latitude'] is not None:
            print(f"緯度: {data['latitude']:.6f}°")
        if 'longitude' in data and data['longitude'] is not None:
            print(f"經度: {data['longitude']:.6f}°")
        if 'altitude' in data and data['altitude'] is not None:
            print(f"海拔: {data['altitude']:.2f} m")
        if 'num_satellites' in data and data['num_satellites'] is not None:
            print(f"衛星數: {data['num_satellites']}")
        if 'fix_quality' in data and data['fix_quality'] is not None:
            quality = {0: '無效', 1: 'GPS', 2: '差分GPS', 3: 'PPS', 
                      4: '即時動態RTK', 5: '浮動RTK', 9: '單獨'}
            print(f"定位品質: {quality.get(data['fix_quality'], '未知')}")
        if 'hdop' in data and data['hdop'] is not None:
            print(f"水平稀釋精度: {data['hdop']}")
        if 'speed_knots' in data and data['speed_knots'] is not None:
            print(f"速度: {data['speed_knots']:.2f} 節 ({float(data['speed_knots'])*1.852:.2f} km/h)")
        if 'fix_type' in data and data['fix_type'] is not None:
            fix_type = {1: '未定位', 2: '2D定位', 3: '3D定位'}
            print(f"定位類型: {fix_type.get(data['fix_type'], '未知')}")
        
        print(f"原始: {data['raw']}")
    
    def run_continuous(self, duration=None):
        """
        連續讀取 GPS 資料
        
        Args:
            duration: 執行時間 (秒)，None 表示無限期執行
        """
        if not self.is_connected:
            print("未連接到 GPS 模組")
            return
        
        print(f"\n開始讀取 GPS 資料... (按 Ctrl+C 停止)")
        print("-" * 50)
        
        start_time = time.time()
        data_count = 0
        
        try:
            while True:
                # 檢查是否超時
                if duration and (time.time() - start_time) > duration:
                    break
                
                data = self.read_gps_data()
                if data:
                    self.print_gps_data(data)
                    data_count += 1
                else:
                    print(".", end="", flush=True)
                
                time.sleep(0.1)
        
        except KeyboardInterrupt:
            print("\n\n已停止讀取")
        finally:
            print(f"共讀取 {data_count} 筆資料")


def main():
    """主程式"""
    import argparse
    
    parser = argparse.ArgumentParser(description='LC29H GPS 模組讀取器')
    parser.add_argument('--port', default='/dev/ttyUSB0', help='串列埠 (預設: /dev/ttyUSB0)')
    parser.add_argument('--baud', type=int, default=115200, help='波特率 (預設: 115200)')
    parser.add_argument('--duration', type=int, help='執行時間 (秒)')
    parser.add_argument('--auto', action='store_true', help='自動偵測波特率')
    parser.add_argument('--debug', action='store_true', help='顯示除錯訊息')
    parser.add_argument('--raw', action='store_true', help='顯示原始串列埠資料 (用於診斷)')
    
    args = parser.parse_args()
    
    # 如果是 raw 模式，直接讀取原始資料
    if args.raw:
        print(f"正在讀取 {args.port} 的原始資料 (波特率: {args.baud})...")
        print("按 Ctrl+C 停止\n")
        try:
            ser = serial.Serial(args.port, args.baud, timeout=1)
            ser.reset_input_buffer()
            while True:
                if ser.in_waiting:
                    data = ser.read(ser.in_waiting)
                    print(f"[HEX] {data.hex()}")
                    print(f"[TXT] {data.decode('utf-8', errors='replace')}")
                time.sleep(0.1)
        except KeyboardInterrupt:
            print("\n已停止")
        except Exception as e:
            print(f"錯誤: {e}")
        sys.exit(0)
    
    # 建立讀取器
    gps = LC29HGPSReader(port=args.port, baudrate=args.baud, debug=args.debug)
    
    # 自動偵測或直接連接
    if args.auto:
        if not gps.auto_detect_baudrate():
            sys.exit(1)
    else:
        if not gps.connect():
            sys.exit(1)
    
    try:
        # 連續讀取資料
        gps.run_continuous(duration=args.duration)
    finally:
        gps.disconnect()


if __name__ == '__main__':
    main()
