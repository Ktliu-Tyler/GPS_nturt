#!/usr/bin/env python3
"""
GPS NMEA Data Decoder and Analyzer
多星座 GPS 資料解碼器
解析 $GNRMC, $GNGGA, $GNGSA, $GPGSV 等 NMEA 句子
"""

import re
from collections import defaultdict
from datetime import datetime

class NMEADecoder:
    """NMEA 句子解碼器"""
    
    # 衛星系統識別符
    CONSTELLATIONS = {
        'GP': 'GPS (美國)',
        'GL': 'GLONASS (俄羅斯)',
        'GA': 'Galileo (歐洲)',
        'GB': 'BeiDou (中國)',
        'GQ': 'QZSS (日本)',
        'GN': 'Multi-GNSS (多星座)'
    }
    
    # 定位品質
    FIX_QUALITY = {
        '0': '無效',
        '1': 'GPS 單獨定位',
        '2': 'DGPS 差分定位',
        '3': 'PPS 精密單點定位',
        '4': 'RTK 實時動態定位',
        '5': 'Float RTK 浮動RTK',
        '9': '單獨'
    }
    
    def __init__(self):
        self.sentences = defaultdict(list)
        self.position = None
        self.satellites = defaultdict(list)
        self.status = {}
        
    def parse_sentence(self, sentence):
        """解析單個 NMEA 句子"""
        if not sentence.startswith('$'):
            return None
        
        # 移除校驗和
        if '*' in sentence:
            sentence = sentence.split('*')[0]
        
        parts = sentence.split(',')
        if len(parts) < 2:
            return None
        
        msg_type = parts[0][1:]  # 移除 '$'
        return self._parse_by_type(msg_type, parts)
    
    def _parse_by_type(self, msg_type, parts):
        """根據句子類型解析"""
        
        # RMC 句子：推薦最小導航訊息
        if 'RMC' in msg_type:
            if len(parts) >= 10:
                return {
                    'type': 'RMC',
                    'full_type': msg_type,
                    'time': parts[1],
                    'status': parts[2],  # A=有效, V=無效
                    'lat': self._parse_lat_lon(parts[3], parts[4]),
                    'lon': self._parse_lat_lon(parts[5], parts[6]),
                    'speed_kt': parts[7],
                    'track_true': parts[8],
                    'date': parts[9]
                }
        
        # GLL 句子：地理位置
        elif 'GLL' in msg_type:
            if len(parts) >= 6:
                return {
                    'type': 'GLL',
                    'full_type': msg_type,
                    'lat': self._parse_lat_lon(parts[1], parts[2]),
                    'lon': self._parse_lat_lon(parts[3], parts[4]),
                    'time': parts[5],
                    'status': parts[6] if len(parts) > 6 else 'V'
                }
        
        # GGA 句子：定位資訊 (3D位置和充分詳情)
        elif 'GGA' in msg_type:
            if len(parts) >= 15:
                return {
                    'type': 'GGA',
                    'full_type': msg_type,
                    'time': parts[1],
                    'lat': self._parse_lat_lon(parts[2], parts[3]),
                    'lon': self._parse_lat_lon(parts[4], parts[5]),
                    'fix_quality': parts[6],
                    'num_satellites': parts[7],
                    'hdop': parts[8],
                    'altitude': parts[9],
                    'alt_unit': parts[10]
                }
        
        # GSA 句子：衛星活動訊息
        elif 'GSA' in msg_type:
            if len(parts) >= 18:
                return {
                    'type': 'GSA',
                    'full_type': msg_type,
                    'mode': parts[1],  # A=自動, M=手動
                    'fix_type': parts[2],  # 1=無, 2=2D, 3=3D
                    'satellites': [s for s in parts[3:15] if s],
                    'pdop': parts[15],
                    'hdop': parts[16],
                    'vdop': parts[17]
                }
        
        # GSV 句子：可見衛星訊息
        elif 'GSV' in msg_type:
            if len(parts) >= 4:
                return {
                    'type': 'GSV',
                    'full_type': msg_type,
                    'total_msgs': parts[1],
                    'msg_num': parts[2],
                    'total_sats': parts[3],
                    'satellites': self._parse_gsv_satellites(parts[4:])
                }
        
        # VTG 句子：地面速度和航向
        elif 'VTG' in msg_type:
            if len(parts) >= 9:
                return {
                    'type': 'VTG',
                    'full_type': msg_type,
                    'track_true': parts[1],
                    'track_mag': parts[3],
                    'speed_kt': parts[5],
                    'speed_kmh': parts[7]
                }
        
        return {'type': msg_type, 'raw': parts}
    
    def _parse_lat_lon(self, value, direction):
        """解析緯度/經度"""
        if not value or not direction:
            return None
        try:
            value = float(value)
            # DDMM.XXXXX 格式轉換為十進制度
            degrees = int(value / 100)
            minutes = value % 100
            decimal = degrees + minutes / 60
            if direction in ['S', 'W']:
                decimal = -decimal
            return round(decimal, 6)
        except:
            return None
    
    def _parse_gsv_satellites(self, parts):
        """解析 GSV 句子中的衛星資訊"""
        satellites = []
        for i in range(0, len(parts), 4):
            if i + 3 <= len(parts):
                sat_info = {
                    'id': parts[i] if i < len(parts) else None,
                    'elevation': parts[i+1] if i+1 < len(parts) else None,
                    'azimuth': parts[i+2] if i+2 < len(parts) else None,
                    'snr': parts[i+3] if i+3 < len(parts) else None
                }
                if sat_info['id']:
                    satellites.append(sat_info)
        return satellites
    
    def decode_hex_data(self, hex_string):
        """解碼十六進制數據為文字"""
        try:
            return bytes.fromhex(hex_string).decode('utf-8', errors='replace')
        except:
            return None
    
    def print_position_summary(self, rmc_data, gga_data):
        """列印位置摘要"""
        print("\n" + "="*60)
        print("📍 GPS 位置資訊")
        print("="*60)
        
        if rmc_data:
            print(f"\n時間: {rmc_data.get('time', 'N/A')}")
            if rmc_data.get('date'):
                print(f"日期: {rmc_data.get('date', 'N/A')}")
            
            lat = rmc_data.get('lat')
            lon = rmc_data.get('lon')
            if lat and lon:
                print(f"緯度: {lat}° {'N' if lat > 0 else 'S'}")
                print(f"經度: {lon}° {'E' if lon > 0 else 'W'}")
                # 顯示為 Google Maps URL
                print(f"  Google Maps: https://maps.google.com/?q={abs(lat)},{abs(lon)}")
            
            print(f"速度: {rmc_data.get('speed_kt', 'N/A')} 節", end="")
            if rmc_data.get('speed_kt') and rmc_data['speed_kt']:
                kmh = float(rmc_data['speed_kt']) * 1.852
                print(f" ({kmh:.2f} km/h)")
            else:
                print()
            
            print(f"航向: {rmc_data.get('track_true', 'N/A')}°")
            print(f"定位狀態: {'✓ 有效' if rmc_data.get('status') == 'A' else '✗ 無效'}")
        
        if gga_data:
            print(f"\n海拔: {gga_data.get('altitude', 'N/A')} {gga_data.get('alt_unit', 'm')}")
            fix_q = gga_data.get('fix_quality', '0')
            print(f"定位品質: {self.FIX_QUALITY.get(fix_q, '未知')}")
            print(f"衛星數: {gga_data.get('num_satellites', 'N/A')}")
            print(f"水平精度 (HDOP): {gga_data.get('hdop', 'N/A')}")
    
    def print_satellite_summary(self, gsa_data, gsv_sentences):
        """列印衛星摘要"""
        print("\n" + "="*60)
        print("🛰️  衛星訊息")
        print("="*60)
        
        if gsa_data:
            fix_type = gsa_data.get('fix_type', '1')
            fix_names = {'1': '未定位', '2': '2D 定位', '3': '3D 定位'}
            print(f"\n定位類型: {fix_names.get(fix_type, '未知')}")
            
            used_sats = gsa_data.get('satellites', [])
            if used_sats:
                print(f"使用中的衛星 ({len(used_sats)}): {', '.join(used_sats)}")
            
            print(f"精度因子:")
            print(f"  PDOP: {gsa_data.get('pdop', 'N/A')} (位置精度因子)")
            print(f"  HDOP: {gsa_data.get('hdop', 'N/A')} (水平精度因子)")
            print(f"  VDOP: {gsa_data.get('vdop', 'N/A')} (垂直精度因子)")
        
        # 統計可見衛星
        print(f"\n可見衛星統計:")
        constellation_count = defaultdict(int)
        signal_strengths = defaultdict(list)
        
        for gsv in gsv_sentences:
            constellation = self.CONSTELLATIONS.get(
                gsv.get('full_type', 'GN')[:2], 'Unknown'
            )
            constellation_count[constellation] += int(gsv.get('total_sats', 0))
            
            for sat in gsv.get('satellites', []):
                snr = sat.get('snr')
                if snr and snr.isdigit():
                    signal_strengths[constellation].append(int(snr))
        
        for constellation, count in sorted(constellation_count.items()):
            avg_signal = 0
            if constellation in signal_strengths:
                signals = signal_strengths[constellation]
                avg_signal = sum(signals) / len(signals) if signals else 0
            print(f"  {constellation}: {count} 顆 (平均信號強度: {avg_signal:.1f} dBHz)")
    
    def analyze_data(self, text_data):
        """分析完整的 GPS 資料"""
        lines = text_data.strip().split('\n')
        
        sentences = {}
        gsa_data = None
        gsv_sentences = []
        
        for line in lines:
            if not line.startswith('$'):
                continue
            
            parsed = self.parse_sentence(line)
            if not parsed:
                continue
            
            msg_type = parsed.get('type')
            
            if msg_type == 'RMC':
                sentences['rmc'] = parsed
            elif msg_type == 'GGA':
                sentences['gga'] = parsed
            elif msg_type == 'GLL':
                sentences['gll'] = parsed
            elif msg_type == 'GSA':
                gsa_data = parsed
            elif msg_type == 'GSV':
                gsv_sentences.append(parsed)
            elif msg_type == 'VTG':
                sentences['vtg'] = parsed
        
        # 列印摘要
        self.print_position_summary(sentences.get('rmc'), sentences.get('gga'))
        self.print_satellite_summary(gsa_data, gsv_sentences)
        
        print("\n" + "="*60)


def main():
    """主程式 - 實時解碼 GPS 資料"""
    import serial
    import sys
    
    print("GPS NMEA 實時解碼器")
    print("連接到 /dev/ttyUSB0 (115200 波特率)")
    print("按 Ctrl+C 停止\n")
    
    decoder = NMEADecoder()
    
    try:
        ser = serial.Serial('/dev/ttyUSB0', 115200, timeout=1)
        ser.reset_input_buffer()
        
        buffer = ""
        sentence_count = 0
        position_count = 0
        
        while True:
            if ser.in_waiting:
                data = ser.read(ser.in_waiting)
                buffer += data.decode('utf-8', errors='replace')
                
                # 處理完整的句子
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    line = line.strip('\r')
                    
                    if line.startswith('$'):
                        sentence_count += 1
                        parsed = decoder.parse_sentence(line)
                        
                        if parsed and parsed.get('type') == 'RMC':
                            position_count += 1
                            print(f"\r位置更新 #{position_count}: ", end="")
                            
                            lat = parsed.get('lat')
                            lon = parsed.get('lon')
                            speed = parsed.get('speed_kt', '0')
                            
                            if lat and lon:
                                print(f"{lat:.4f}°, {lon:.4f}° @ {speed} 節", end="", flush=True)
            
            else:
                # 定期顯示詳細統計
                pass
    
    except KeyboardInterrupt:
        print(f"\n\n已停止 (共接收 {sentence_count} 句 NMEA 資訊)")
    except Exception as e:
        print(f"錯誤: {e}")


if __name__ == '__main__':
    import sys
    
    # 如果有命令行參數，從標準輸入讀取資料
    if len(sys.argv) > 1 and sys.argv[1] == '--analyze':
        print("請貼上 NMEA 資料 (Ctrl+D 結束):")
        data = sys.stdin.read()
        
        decoder = NMEADecoder()
        decoder.analyze_data(data)
    else:
        # 否則實時讀取
        main()
