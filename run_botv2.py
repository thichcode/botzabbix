#!/usr/bin/env python3
"""
Script để chạy Zabbix Telegram Bot v2.0
Sử dụng thư viện telebot
"""

import sys
import os

# Thêm thư mục hiện tại vào Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from botv2 import main

if __name__ == '__main__':
    print("🚀 Khởi động Zabbix Telegram Bot v2.0...")
    print("📱 Sử dụng thư viện telebot")
    print("=" * 50)
    
    try:
        main()
    except KeyboardInterrupt:
        print("\n⏹️ Bot đã được dừng bởi người dùng")
    except Exception as e:
        print(f"❌ Lỗi khi chạy bot: {e}")
        sys.exit(1) 