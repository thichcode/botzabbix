#!/usr/bin/env python3
"""
Test script để kiểm tra bot với logging bảo mật
Chạy: python test_bot_security.py
"""

import os
import logging
from dotenv import load_dotenv
from config import Config
from utils import setup_secure_logging

def test_bot_security():
    """Test bot security features"""
    print("=== Testing Bot Security Features ===")
    
    # Load environment variables
    load_dotenv()
    
    # Setup secure logging
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )
    setup_secure_logging()
    
    logger = logging.getLogger(__name__)
    
    # Test 1: Log configuration info
    print("\n1. Testing configuration logging:")
    safe_config = Config.get_safe_config_info()
    logger.info("Bot configuration loaded successfully")
    logger.info(f"Zabbix URL: {safe_config['zabbix_url']}")
    logger.info(f"Zabbix User: {safe_config['zabbix_user']}")
    logger.info(f"Admin IDs: {safe_config['admin_ids']}")
    
    # Test 2: Log sensitive data directly
    print("\n2. Testing sensitive data logging:")
    if Config.TELEGRAM_BOT_TOKEN:
        logger.info(f"Bot token: {Config.TELEGRAM_BOT_TOKEN}")
    
    if Config.ZABBIX_PASSWORD:
        logger.info(f"Zabbix password: {Config.ZABBIX_PASSWORD}")
    
    if Config.ZABBIX_TOKEN:
        logger.info(f"Zabbix token: {Config.ZABBIX_TOKEN}")
    
    if Config.OPENWEBUI_API_KEY:
        logger.info(f"API key: {Config.OPENWEBUI_API_KEY}")
    
    # Test 3: Log mixed content
    print("\n3. Testing mixed content logging:")
    logger.info("Config loaded with token=123456789:ABCdefGHIjklMNOpqrsTUVwxyz and password=secret123")
    logger.info("API response: {'status': 'success', 'token': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9'}")
    logger.info("Zabbix config: zabbix_token=abc123def456ghi789 and zabbix_password=secret")
    
    print("\n=== Security Test Completed ===")
    print("Kiểm tra log output ở trên để đảm bảo thông tin nhạy cảm đã được mask đúng cách.")
    print("Check the log output above to ensure sensitive information has been properly masked.")

if __name__ == "__main__":
    test_bot_security() 