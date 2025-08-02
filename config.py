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
    ZABBIX_TOKEN = os.getenv('ZABBIX_TOKEN')  # API token for Zabbix 5.4+
    BYPASS_SSL = os.getenv('BYPASS_SSL', 'false').lower() == 'true'
    
    # Host Groups for filtering problems
    HOST_GROUPS = [group.strip() for group in os.getenv('HOST_GROUPS', '').split(',') if group.strip()]
    
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
            
        # Check if either token or password is provided
        if not cls.ZABBIX_TOKEN and not cls.ZABBIX_PASSWORD:
            errors.append("Either ZABBIX_TOKEN or ZABBIX_PASSWORD is required")
            
        return errors
    
    @classmethod
    def get_safe_config_info(cls) -> dict:
        """Get configuration info with sensitive data masked"""
        return {
            'telegram_bot_token': f"{cls.TELEGRAM_BOT_TOKEN[:8]}*****" if cls.TELEGRAM_BOT_TOKEN else None,
            'admin_ids': cls.ADMIN_IDS,
            'zabbix_url': cls.ZABBIX_URL,
            'zabbix_user': cls.ZABBIX_USER,
            'zabbix_password': '*****' if cls.ZABBIX_PASSWORD else None,
            'zabbix_token': f"{cls.ZABBIX_TOKEN[:8]}*****" if cls.ZABBIX_TOKEN else None,
            'openwebui_api_key': f"{cls.OPENWEBUI_API_KEY[:8]}*****" if cls.OPENWEBUI_API_KEY else None,
            'host_groups': cls.HOST_GROUPS,
            'screenshot_width': cls.SCREENSHOT_WIDTH,
            'screenshot_height': cls.SCREENSHOT_HEIGHT,
            'db_path': cls.DB_PATH,
            'data_retention_period': cls.DATA_RETENTION_PERIOD
        } 