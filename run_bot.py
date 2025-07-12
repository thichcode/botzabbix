#!/usr/bin/env python3
"""
Simple script to run the Zabbix Telegram Bot
"""

import os
import sys
import logging

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def main():
    """Main function to run the bot"""
    try:
        # Check if .env file exists
        if not os.path.exists('.env'):
            print("❌ File .env không tồn tại!")
            print("📝 Vui lòng tạo file .env dựa trên env_example.txt")
            print("💡 Hoặc chạy: cp env_example.txt .env")
            return
        
        # Import and run bot
        from bot import main as run_bot
        print("🚀 Đang khởi động Zabbix Telegram Bot...")
        run_bot()
        
    except ImportError as e:
        print(f"❌ Lỗi import: {e}")
        print("💡 Vui lòng cài đặt dependencies: pip install -r requirements.txt")
    except Exception as e:
        print(f"❌ Lỗi khởi động bot: {e}")
        logging.error(f"Bot startup error: {e}")

if __name__ == "__main__":
    main() 