#!/usr/bin/env python3
"""
GPS 诊断工具 - 测量实际输出频率和句子类型
"""

import serial
import time
from collections import defaultdict

def diagnose_gps(port='/dev/ttyUSB0', baudrate=115200, duration=10):
    """诊断 GPS 输出频率"""
    
    try:
        ser = serial.Serial(port, baudrate, timeout=1)
        ser.reset_input_buffer()
    except Exception as e:
        print(f"❌ 无法连接: {e}")
        return
    
    print(f"正在诊断 {port} (采样 {duration} 秒)...\n")
    
    start_time = time.time()
    buffer = ""
    sentence_count = defaultdict(int)
    total_bytes = 0
    
    try:
        while time.time() - start_time < duration:
            if ser.in_waiting:
                chunk = ser.read(ser.in_waiting)
                total_bytes += len(chunk)
                buffer += chunk.decode('utf-8', errors='ignore')
                
                # 处理完整句子
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    line = line.strip('\r\n')
                    
                    if line.startswith('$'):
                        # 提取句子类型
                        parts = line.split(',')
                        msg_type = parts[0][1:] if len(parts) > 0 else 'UNKNOWN'
                        sentence_count[msg_type] += 1
            
            time.sleep(0.001)
    
    except KeyboardInterrupt:
        pass
    finally:
        ser.close()
    
    elapsed = time.time() - start_time
    
    # 打印结果
    print("="*70)
    print("📊 GPS 输出诊断结果")
    print("="*70)
    print(f"\n采样时间: {elapsed:.2f} 秒")
    print(f"接收字节: {total_bytes} 字节")
    print(f"波特率效率: {(total_bytes * 8 / elapsed / 1000):.1f} kbit/s (理论: 115.2 kbit/s)")
    
    total_sentences = sum(sentence_count.values())
    print(f"\n📈 总句子数: {total_sentences} 句")
    print(f"   平均频率: {(total_sentences / elapsed):.1f} 句/秒")
    
    print(f"\n📋 句子类型分布:")
    for msg_type in sorted(sentence_count.keys()):
        count = sentence_count[msg_type]
        pct = (count / total_sentences * 100) if total_sentences > 0 else 0
        freq = count / elapsed
        print(f"   {msg_type:10s}: {count:4d} 句 ({pct:5.1f}%) | {freq:5.1f} 句/秒")
    
    print(f"\n💡 建议:")
    if total_sentences / elapsed < 5:
        print("   ⚠️  GPS 输出频率较低 (< 5 Hz)")
        print("      可能需要配置 GPS 输出频率更高")
        print("      检查 GPS 模块设置 (nmea 消息频率)")
    else:
        print(f"   ✓ GPS 输出频率良好 ({total_sentences / elapsed:.1f} Hz)")
    
    print("\n" + "="*70)


if __name__ == '__main__':
    import sys
    duration = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    diagnose_gps(duration=duration)
