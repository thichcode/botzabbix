import os
from typing import List
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Telegram Bot
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    ADMIN_IDS = [int(id) for id in os.getenv('ADMIN_IDS', '').split(',') if id]
    TELEGRAM_PROXY_URL = os.getenv('TELEGRAM_PROXY_URL')
    USE_PROXY = os.getenv('USE_PROXY', 'false').lower() == 'true'
    
    # Zabbix
    ZABBIX_URL = os.getenv('ZABBIX_URL')
    ZABBIX_USER = os.getenv('ZABBIX_USER')
    ZABBIX_PASSWORD = os.getenv('ZABBIX_PASSWORD')
    BYPASS_SSL = os.getenv('BYPASS_SSL', 'false').lower() == 'true'
    
    # Screenshot
    SCREENSHOT_WIDTH = int(os.getenv('SCREENSHOT_WIDTH', '1920'))
    SCREENSHOT_HEIGHT = int(os.getenv('SCREENSHOT_HEIGHT', '1080'))
    
    # AI Integration
    OPENWEBUI_API_URL = os.getenv('OPENWEBUI_API_URL')
    OPENWEBUI_API_KEY = os.getenv('OPENWEBUI_API_KEY')
    
    # Database
    DB_PATH = 'zabbix_alerts.db'
    DB_TIMEOUT = 10
    DATA_RETENTION_PERIOD = 90 * 24 * 60 * 60  # 90 days
    
    @classmethod
    def validate(cls) -> List[str]:
        """Validate required configuration"""
        errors = []
        
        if not cls.TELEGRAM_BOT_TOKEN:
            errors.append("TELEGRAM_BOT_TOKEN is required")
        
        if not cls.ADMIN_IDS:
            errors.append("ADMIN_IDS is required")
            
        if not cls.ZABBIX_URL:
            errors.append("ZABBIX_URL is required")
            
        if not cls.ZABBIX_USER:
            errors.append("ZABBIX_USER is required")
            
        if not cls.ZABBIX_PASSWORD:
            errors.append("ZABBIX_PASSWORD is required")
            
        return errors 