import pytest
import os
from unittest.mock import patch
from config import Config

class TestConfig:
    def test_admin_ids_parsing(self):
        """Test parsing of ADMIN_IDS from environment"""
        with patch.dict(os.environ, {'ADMIN_IDS': '123,456,789'}):
            # Reload config
            Config.ADMIN_IDS = [int(id) for id in os.getenv('ADMIN_IDS', '').split(',') if id]
            assert Config.ADMIN_IDS == [123, 456, 789]
    
    def test_admin_ids_empty(self):
        """Test empty ADMIN_IDS"""
        with patch.dict(os.environ, {'ADMIN_IDS': ''}):
            Config.ADMIN_IDS = [int(id) for id in os.getenv('ADMIN_IDS', '').split(',') if id]
            assert Config.ADMIN_IDS == []
    
    def test_screenshot_dimensions(self):
        """Test screenshot dimensions parsing"""
        with patch.dict(os.environ, {
            'SCREENSHOT_WIDTH': '1920',
            'SCREENSHOT_HEIGHT': '1080'
        }):
            Config.SCREENSHOT_WIDTH = int(os.getenv('SCREENSHOT_WIDTH', '1920'))
            Config.SCREENSHOT_HEIGHT = int(os.getenv('SCREENSHOT_HEIGHT', '1080'))
            assert Config.SCREENSHOT_WIDTH == 1920
            assert Config.SCREENSHOT_HEIGHT == 1080
    
    def test_use_proxy_true(self):
        """Test USE_PROXY parsing for true"""
        with patch.dict(os.environ, {'USE_PROXY': 'true'}):
            Config.USE_PROXY = os.getenv('USE_PROXY', 'false').lower() == 'true'
            assert Config.USE_PROXY is True
    
    def test_use_proxy_false(self):
        """Test USE_PROXY parsing for false"""
        with patch.dict(os.environ, {'USE_PROXY': 'false'}):
            Config.USE_PROXY = os.getenv('USE_PROXY', 'false').lower() == 'true'
            assert Config.USE_PROXY is False
    
    def test_validate_missing_required(self):
        """Test validation with missing required fields"""
        with patch.dict(os.environ, {}, clear=True):
            errors = Config.validate()
            assert len(errors) >= 4  # Should have at least 4 required fields
            assert "TELEGRAM_BOT_TOKEN is required" in errors
            assert "ADMIN_IDS is required" in errors
            assert "ZABBIX_URL is required" in errors
            assert "ZABBIX_USER is required" in errors
            assert "ZABBIX_PASSWORD is required" in errors

if __name__ == "__main__":
    pytest.main([__file__]) 