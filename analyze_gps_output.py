#!/usr/bin/env python3
"""
快速解碼上次 GPS 輸出
Quickly decode the recent GPS output you provided
"""

# 從你的輸出擷取的 NMEA 句子
gps_output = """$GNRMC,062407.000,A,2502.263097,N,12125.095779,E,20.905,032.71,010326,,,A,V*0E
$GNGLL,2502.263097,N,12125.095779,E,062407.000,A,A*4C
$GNVTG,032.71,T,,M,20.905,N,38.713,K,A*24
$GNGSA,A,3,01,02,03,06,07,08,14,17,22,30,,,1.14,0.62,0.95,1*04
$GPGSV,3,1,09,01,37,034,27,02,09,046,36,03,51,093,30,06,30,243,21,1*69
$GLGSV,2,1,06,70,07,057,17,71,11,112,21,75,41,171,24,76,69,293,30,1*7D
$GAGSV,2,1,06,13,76,298,31,15,35,033,28,21,49,326,33,26,30,232,20,7*73
$GBGSV,6,1,24,01,,,29,03,56,203,25,04,,,28,06,38,212,23,1*78
$GNGLL,2502.288827,N,12125.116999,E,062411.000,A,A*47
$GNVTG,019.96,T,,M,24.259,N,44.924,K,A*23
$GNRMC,062414.000,A,2502.294295,N,12125.117818,E,015.699,343.92,010326,,,A,V*04
$GNVTG,343.92,T,,M,15.699,N,29.072,K,A*20
$GNGSA,A,3,01,02,03,06,07,14,17,22,30,,,,0.89,0.47,0.75,1*00
$GPGSV,3,1,09,01,37,034,28,02,09,046,29,03,51,093,27,06,30,243,25,1*6A"""

import re
from datetime import datetime

class QuickGPSDecoder:
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
    
    def analyze(self, data):
        """分析 GPS 資料"""
        lines = data.strip().split('\n')
        
        positions = []
        speeds = []
        satellites_used = set()
        satellites_visible = defaultdict(int)
        
        for line in lines:
            if not line.startswith('$'):
                continue
            
            parts = line.split('*')[0].split(',')
            msg_type = parts[0][1:]
            
            # RMC 句子 - 位置和速度
            if 'RMC' in msg_type:
                try:
                    lat = self.parse_lat_lon(parts[3], parts[4])
                    lon = self.parse_lat_lon(parts[5], parts[6])
                    speed = float(parts[7]) if parts[7] else 0
                    track = parts[8] if parts[8] else 'N/A'
                    time = parts[1]
                    date = parts[9] if len(parts) > 9 else 'N/A'
                    
                    if lat and lon:
                        positions.append({
                            'time': time,
                            'date': date,
                            'lat': lat,
                            'lon': lon,
                            'speed': speed,
                            'track': track
                        })
                        speeds.append(speed)
                except:
                    pass
            
            # VTG 句子 - 詳細速度資訊
            elif 'VTG' in msg_type:
                try:
                    track_true = parts[1]
                    speed_kt = parts[5]
                    speed_kmh = parts[7]
                    if speed_kt:
                        print(f"  速度: {speed_kt} 節 = {speed_kmh} km/h, 航向: {track_true}°")
                except:
                    pass
            
            # GSA 句子 - 使用的衛星
            elif 'GSA' in msg_type:
                try:
                    fix_type = parts[2]
                    fix_types = {'1': '未定位', '2': '2D 定位', '3': '3D 定位'}
                    sats = [p for p in parts[3:15] if p]
                    pdop = parts[15] if len(parts) > 15 else 'N/A'
                    hdop = parts[16] if len(parts) > 16 else 'N/A'
                    vdop = parts[17] if len(parts) > 17 else 'N/A'
                    
                    for sat in sats:
                        satellites_used.add(sat)
                except:
                    pass
            
            # GSV 句子 - 可見衛星
            elif 'GSV' in msg_type:
                try:
                    total_sats = int(parts[3])
                    constellation = msg_type[:2]  # GP, GL, GA, GB
                    satellites_visible[constellation] += total_sats
                except:
                    pass
        
        # 列印結果
        print("\n" + "="*70)
        print("🌍 GPS 資料解碼報告")
        print("="*70)
        
        if positions:
            print(f"\n📍 位置軌跡 (共 {len(positions)} 個位置):")
            for i, pos in enumerate(positions, 1):
                print(f"\n  #{i} @ {pos['time']}")
                print(f"    座標: {pos['lat']:.6f}°N, {pos['lon']:.6f}°E")
                print(f"    Google Maps: https://maps.google.com/?q={pos['lat']:.6f},{pos['lon']:.6f}")
                print(f"    速度: {pos['speed']:.3f} 節 ({float(pos['speed'])*1.852:.2f} km/h)")
                print(f"    航向: {pos['track']}°")
        
        if speeds:
            avg_speed = sum(speeds) / len(speeds)
            max_speed = max(speeds)
            print(f"\n📊 速度統計:")
            print(f"  平均速度: {avg_speed:.3f} 節 ({avg_speed*1.852:.2f} km/h)")
            print(f"  最高速度: {max_speed:.3f} 節 ({max_speed*1.852:.2f} km/h)")
        
        if satellites_used:
            print(f"\n🛰️  衛星資訊:")
            print(f"  使用中的衛星: {', '.join(sorted(satellites_used))} (共 {len(satellites_used)} 顆)")
        
        if satellites_visible:
            print(f"\n  可見衛星統計:")
            constellations = {
                'GP': 'GPS (美國)',
                'GL': 'GLONASS (俄羅斯)',
                'GA': 'Galileo (歐洲)',
                'GB': 'BeiDou (中國)',
                'GQ': 'QZSS (日本)'
            }
            for const, count in sorted(satellites_visible.items()):
                name = constellations.get(const, const)
                print(f"    {name}: {count} 顆")
        
        print("\n" + "="*70)


if __name__ == '__main__':
    from collections import defaultdict
    decoder = QuickGPSDecoder()
    decoder.analyze(gps_output)
