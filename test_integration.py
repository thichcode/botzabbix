import pytest
import asyncio
import os
from unittest.mock import Mock, patch, AsyncMock
from telegram import Update, User, Chat
from telegram.ext import ContextTypes

from config import Config
from decorators import admin_only, validate_input
from utils import retry, safe_int, format_timestamp, truncate_text, validate_url
from commands.get_alerts import GetAlertsCommand
from commands.ask_ai import AskAiCommand

class TestIntegration:
    """Integration tests for the bot system"""
    
    def setup_method(self):
        """Setup test environment"""
        # Mock environment variables
        self.env_patcher = patch.dict(os.environ, {
            'TELEGRAM_BOT_TOKEN': 'test_token',
            'ADMIN_IDS': '123,456',
            'ZABBIX_URL': 'http://test-zabbix.com',
            'ZABBIX_USER': 'test_user',
            'ZABBIX_PASSWORD': 'test_pass'
        })
        self.env_patcher.start()
        
        # Reload config
        import importlib
        import config
        importlib.reload(config)
        from config import Config
        self.Config = Config
    
    def teardown_method(self):
        """Cleanup test environment"""
        self.env_patcher.stop()
    
    def test_config_validation(self):
        """Test configuration validation"""
        errors = self.Config.validate()
        assert len(errors) == 0, f"Config validation failed: {errors}"
    
    def test_admin_ids_parsing(self):
        """Test admin IDs parsing"""
        assert self.Config.ADMIN_IDS == [123, 456]
    
    def test_utils_functions(self):
        """Test utility functions"""
        # Test safe_int
        assert safe_int("123") == 123
        assert safe_int("abc", default=0) == 0
        
        # Test format_timestamp
        timestamp = 1640995200  # 2022-01-01 00:00:00
        formatted = format_timestamp(timestamp)
        assert "2022-01-01" in formatted
        
        # Test truncate_text
        long_text = "A" * 200
        truncated = truncate_text(long_text, max_length=100)
        assert len(truncated) == 100
        assert truncated.endswith("...")
        
        # Test validate_url
        assert validate_url("https://example.com") is True
        assert validate_url("http://localhost:8080") is True
        assert validate_url("invalid-url") is False
    
    @pytest.mark.asyncio
    async def test_retry_decorator(self):
        """Test retry decorator"""
        call_count = 0
        
        @retry(max_attempts=3, delay=0.1)
        async def failing_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("Temporary failure")
            return "success"
        
        result = await failing_function()
        assert result == "success"
        assert call_count == 3
    
    @pytest.mark.asyncio
    async def test_admin_only_decorator(self):
        """Test admin only decorator"""
        # Create mock update and context
        update = Mock(spec=Update)
        update.effective_user = Mock(spec=User)
        update.effective_user.id = 123  # Admin ID
        update.message = Mock()
        update.message.reply_text = AsyncMock()
        
        context = Mock(spec=ContextTypes.DEFAULT_TYPE)
        
        # Test with admin user
        @admin_only
        async def test_command(self, update, context):
            return "success"
        
        result = await test_command(None, update, context)
        assert result == "success"
        
        # Test with non-admin user
        update.effective_user.id = 999  # Non-admin ID
        await test_command(None, update, context)
        update.message.reply_text.assert_called_with("Bạn không có quyền sử dụng lệnh này.")
    
    @pytest.mark.asyncio
    async def test_validate_input_decorator(self):
        """Test input validation decorator"""
        update = Mock(spec=Update)
        update.message = Mock()
        update.message.reply_text = AsyncMock()
        
        context = Mock(spec=ContextTypes.DEFAULT_TYPE)
        context.args = ["test", "input"]
        
        # Test with valid input
        @validate_input(max_length=100)
        async def test_command(self, update, context):
            return "success"
        
        result = await test_command(None, update, context)
        assert result == "success"
        
        # Test with too long input
        context.args = ["A" * 200]
        await test_command(None, update, context)
        update.message.reply_text.assert_called_with("Input quá dài. Tối đa 100 ký tự.")
    
    @pytest.mark.asyncio
    async def test_get_alerts_command(self):
        """Test get alerts command"""
        # Mock Zabbix API
        mock_zapi = Mock()
        mock_zapi.trigger.get.return_value = [
            {
                'triggerid': '123',
                'description': 'Test alert',
                'priority': '3',
                'lastchange': '1640995200',
                'hosts': [{'host': 'test-host'}]
            }
        ]
        
        with patch('commands.get_alerts.get_zabbix_api', return_value=mock_zapi):
            with patch('commands.get_alerts.save_alert'):
                with patch('commands.get_alerts.send_alert_with_screenshot', new_callable=AsyncMock):
                    command = GetAlertsCommand()
                    
                    # Create mock update and context
                    update = Mock(spec=Update)
                    update.effective_user = Mock(spec=User)
                    update.effective_user.id = 123  # Admin ID
                    update.effective_chat = Mock(spec=Chat)
                    update.effective_chat.id = 456
                    update.message = Mock()
                    update.message.reply_text = AsyncMock()
                    
                    context = Mock(spec=ContextTypes.DEFAULT_TYPE)
                    
                    await command.execute(update, context)
                    
                    # Verify API was called
                    mock_zapi.trigger.get.assert_called_once()
                    
                    # Verify messages were sent
                    assert update.message.reply_text.call_count >= 1
    
    @pytest.mark.asyncio
    async def test_ask_ai_command(self):
        """Test ask AI command"""
        # Mock Zabbix API
        mock_zapi = Mock()
        mock_zapi.trigger.get.return_value = []
        mock_zapi.host.get.return_value = []
        
        # Mock requests
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'choices': [{'message': {'content': 'AI response'}}]
        }
        
        with patch('commands.ask_ai.get_zabbix_api', return_value=mock_zapi):
            with patch('commands.ask_ai.requests.post', return_value=mock_response):
                command = AskAiCommand()
                
                # Create mock update and context
                update = Mock(spec=Update)
                update.effective_user = Mock(spec=User)
                update.effective_user.id = 123  # Admin ID
                update.message = Mock()
                update.message.reply_text = AsyncMock()
                
                context = Mock(spec=ContextTypes.DEFAULT_TYPE)
                context.args = ["What is the status?"]
                
                await command.execute(update, context)
                
                # Verify messages were sent
                assert update.message.reply_text.call_count >= 1

if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 