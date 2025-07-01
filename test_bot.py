import unittest
import os
import time
from unittest.mock import patch, MagicMock, AsyncMock
from telegram import Update, User, Chat
from telegram.ext import ContextTypes
from bot import (
    init_db, save_user, get_user, remove_user, extract_url_from_text,
    save_alert, get_alerts, take_screenshot, get_zabbix_api, get_hosts, get_graph,
    add_error_pattern, get_error_patterns, remove_error_pattern,
    add_host_website, get_host_website, remove_host_website,
    send_alert_with_screenshot, process_alerts_batch, cleanup_old_data,
    get_db_connection
)
import pytest

test_db = 'test_zabbix_alerts.db'

class TestBotRealDB(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Tạo database test
        if os.path.exists(test_db):
            os.remove(test_db)
        init_db(test_db)

    @classmethod
    def tearDownClass(cls):
        # Xóa database test
        if os.path.exists(test_db):
            os.remove(test_db)

    def setUp(self):
        self.user_id = 1001
        self.username = 'realuser'
        self.first_name = 'Real'
        self.last_name = 'User'
        
        # Mock Telegram objects
        self.mock_user = User(
            id=self.user_id,
            is_bot=False,
            first_name=self.first_name,
            last_name=self.last_name,
            username=self.username
        )
        self.mock_chat = Chat(
            id=123456,
            type='private'
        )
        self.mock_update = Update(
            update_id=1,
            message=MagicMock(
                from_user=self.mock_user,
                chat=self.mock_chat
            )
        )
        self.mock_context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)

    def test_save_and_get_user(self):
        result = save_user(self.user_id, self.username, self.first_name, self.last_name, test_db)
        self.assertTrue(result)
        user = get_user(self.user_id, test_db)
        self.assertIsNotNone(user)
        self.assertEqual(user['username'], self.username)
        self.assertEqual(user['first_name'], self.first_name)
        self.assertEqual(user['last_name'], self.last_name)
        self.assertTrue(user['is_active'])

    def test_remove_user(self):
        save_user(self.user_id, self.username, self.first_name, self.last_name, test_db)
        result = remove_user(self.user_id, test_db)
        self.assertTrue(result)
        user = get_user(self.user_id, test_db)
        self.assertIsNotNone(user)
        self.assertFalse(user['is_active'])

    def test_extract_url(self):
        self.assertEqual(
            extract_url_from_text('visit https://abc.com now'),
            'https://abc.com'
        )
        self.assertIsNone(
            extract_url_from_text('no url here')
        )
        self.assertEqual(
            extract_url_from_text('a https://a.com b https://b.com'),
            'https://a.com'
        )

    def test_save_and_get_alerts(self):
        # Test data
        alert_data = {
            'trigger_id': '12345',
            'host': 'test-host',
            'description': 'Test alert',
            'priority': 3,
            'timestamp': int(time.time())
        }
        
        # Save alert
        result = save_alert(
            alert_data['trigger_id'],
            alert_data['host'],
            alert_data['description'],
            alert_data['priority'],
            alert_data['timestamp'],
            test_db
        )
        self.assertTrue(result)

    @pytest.mark.asyncio
    @patch('bot.webdriver.Chrome')
    async def test_take_screenshot(self, mock_chrome):
        # Mock Chrome driver
        mock_driver = MagicMock()
        mock_chrome.return_value = mock_driver
        mock_driver.get_screenshot_as_png.return_value = b'test_screenshot'

        # Test successful screenshot
        result = await take_screenshot('https://example.com')
        self.assertEqual(result, b'test_screenshot')
        mock_driver.quit.assert_called_once()

        # Test screenshot error
        mock_driver.get_screenshot_as_png.side_effect = Exception('Screenshot failed')
        with pytest.raises(Exception):
            await take_screenshot('https://example.com')

    @patch('bot.get_zabbix_api')
    async def test_get_alerts(self, mock_zabbix_api):
        # Mock Zabbix API response
        mock_zapi = MagicMock()
        mock_zapi.trigger.get.return_value = [
            {
                'triggerid': '12345',
                'description': 'Test alert',
                'priority': 3,
                'lastchange': str(int(time.time())),
                'hosts': [{'host': 'test-host'}]
            }
        ]
        mock_zabbix_api.return_value = mock_zapi

        # Test get_alerts
        await get_alerts(self.mock_update, self.mock_context)
        
        # Verify API was called
        mock_zapi.trigger.get.assert_called_once()
        
        # Verify alert was saved to database
        with get_db_connection(test_db) as conn:
            c = conn.cursor()
            c.execute('SELECT * FROM alerts WHERE trigger_id = ?', ('12345',))
            alert = c.fetchone()
            self.assertIsNotNone(alert)
            self.assertEqual(alert['host'], 'test-host')
            self.assertEqual(alert['description'], 'Test alert')

    @patch('bot.get_zabbix_api')
    async def test_get_hosts(self, mock_zabbix_api):
        # Mock Zabbix API response
        mock_zapi = MagicMock()
        mock_zapi.host.get.return_value = [
            {
                'hostid': '12345',
                'host': 'test-host',
                'status': '0'
            }
        ]
        mock_zabbix_api.return_value = mock_zapi

        # Test get_hosts
        await get_hosts(self.mock_update, self.mock_context)
        
        # Verify API was called
        mock_zapi.host.get.assert_called_once()
        
        # Verify message was sent
        self.mock_context.bot.send_message.assert_called_once()

    @patch('bot.get_zabbix_api')
    async def test_get_graph(self, mock_zabbix_api):
        # Mock Zabbix API response
        mock_zapi = MagicMock()
        mock_zapi.history.get.return_value = [
            {'clock': str(int(time.time())), 'value': '100'}
        ]
        mock_zabbix_api.return_value = mock_zapi

        # Test get_graph
        self.mock_update.message.text = '/graph test-host CPU'
        await get_graph(self.mock_update, self.mock_context)
        
        # Verify API was called
        mock_zapi.history.get.assert_called_once()
        
        # Verify graph was sent
        self.mock_context.bot.send_photo.assert_called_once()

    def test_error_patterns(self):
        # Test add error pattern
        pattern = "Error: Connection refused"
        result = add_error_pattern(pattern, test_db)
        self.assertTrue(result)

        # Test get error patterns
        patterns = get_error_patterns(test_db)
        self.assertIn(pattern, patterns)

        # Test remove error pattern
        result = remove_error_pattern(pattern, test_db)
        self.assertTrue(result)
        patterns = get_error_patterns(test_db)
        self.assertNotIn(pattern, patterns)

    def test_host_websites(self):
        # Test add host website
        host = "test-host"
        website = "https://test-host.com"
        result = add_host_website(host, website, test_db)
        self.assertTrue(result)

        # Test get host website
        saved_website = get_host_website(host, test_db)
        self.assertEqual(saved_website, website)

        # Test remove host website
        result = remove_host_website(host, test_db)
        self.assertTrue(result)
        saved_website = get_host_website(host, test_db)
        self.assertIsNone(saved_website)

    @patch('bot.take_screenshot')
    async def test_send_alert_with_screenshot(self, mock_take_screenshot):
        # Mock screenshot
        mock_take_screenshot.return_value = b'test_screenshot'

        # Test alert with URL
        alert = {
            'host': 'test-host',
            'description': 'Test alert https://test-host.com',
            'priority': 3
        }
        await send_alert_with_screenshot(alert, self.mock_context)
        
        # Verify screenshot was taken
        mock_take_screenshot.assert_called_once_with('https://test-host.com')
        
        # Verify message and photo were sent
        self.mock_context.bot.send_message.assert_called_once()
        self.mock_context.bot.send_photo.assert_called_once()

        # Test alert without URL
        alert = {
            'host': 'test-host',
            'description': 'Test alert without URL',
            'priority': 3
        }
        await send_alert_with_screenshot(alert, self.mock_context)
        
        # Verify only message was sent
        self.mock_context.bot.send_message.assert_called()
        self.mock_context.bot.send_photo.assert_called_once()  # Still once from previous call

    @patch('bot.get_zabbix_api')
    async def test_process_alerts_batch(self, mock_zabbix_api):
        # Mock Zabbix API response
        mock_zapi = MagicMock()
        mock_zapi.trigger.get.return_value = [
            {
                'triggerid': '12345',
                'description': 'Test alert',
                'priority': 3,
                'lastchange': str(int(time.time())),
                'hosts': [{'host': 'test-host'}]
            }
        ]
        mock_zabbix_api.return_value = mock_zapi

        # Test process alerts batch
        alerts = [
            {
                'triggerid': '12345',
                'description': 'Test alert',
                'priority': 3,
                'lastchange': str(int(time.time())),
                'hosts': [{'host': 'test-host'}]
            }
        ]
        await process_alerts_batch(alerts, self.mock_context)
        
        # Verify alert was saved
        with get_db_connection(test_db) as conn:
            c = conn.cursor()
            c.execute('SELECT * FROM alerts WHERE trigger_id = ?', ('12345',))
            alert = c.fetchone()
            self.assertIsNotNone(alert)

    def test_cleanup_old_data(self):
        # Add test data
        old_timestamp = int(time.time()) - 8 * 24 * 3600  # 8 days ago
        new_timestamp = int(time.time()) - 2 * 24 * 3600  # 2 days ago

        # Add old alert
        save_alert('old_trigger', 'old_host', 'Old alert', 3, old_timestamp, test_db)
        
        # Add new alert
        save_alert('new_trigger', 'new_host', 'New alert', 3, new_timestamp, test_db)
        
        # Add old error pattern
        add_error_pattern('old_pattern', test_db)
        # Update last_updated về thời điểm cũ
        with get_db_connection(test_db) as conn:
            c = conn.cursor()
            c.execute('UPDATE error_patterns SET last_updated = ? WHERE pattern = ?', (old_timestamp, 'old_pattern'))
            conn.commit()
        
        # Add new error pattern
        add_error_pattern('new_pattern', test_db)
        
        # Run cleanup với retention_period = 7 ngày
        cleanup_old_data(test_db, retention_period=7*24*3600)
        
        # Verify old data was removed
        with get_db_connection(test_db) as conn:
            c = conn.cursor()
            
            # Check alerts
            c.execute('SELECT * FROM alerts WHERE trigger_id = ?', ('old_trigger',))
            old_alert = c.fetchone()
            self.assertIsNone(old_alert)
            
            c.execute('SELECT * FROM alerts WHERE trigger_id = ?', ('new_trigger',))
            new_alert = c.fetchone()
            self.assertIsNotNone(new_alert)
            
            # Check error patterns
            c.execute('SELECT * FROM error_patterns WHERE pattern = ?', ('old_pattern',))
            old_pattern = c.fetchone()
            self.assertIsNone(old_pattern)
            
            c.execute('SELECT * FROM error_patterns WHERE pattern = ?', ('new_pattern',))
            new_pattern = c.fetchone()
            self.assertIsNotNone(new_pattern)

    @patch('bot.take_screenshot')
    async def test_alert_with_error_pattern_and_screenshot(self, mock_take_screenshot):
        # Mock screenshot
        mock_take_screenshot.return_value = b'test_screenshot'
        
        # Add error pattern
        pattern = "Error: Connection refused"
        add_error_pattern(pattern, test_db)
        
        # Add host website
        host = "test-host"
        website = "https://test-host.com"
        add_host_website(host, website, test_db)
        
        # Test alert with error pattern and URL
        alert = {
            'host': host,
            'description': f'Test alert with {pattern} {website}',
            'priority': 3
        }
        await send_alert_with_screenshot(alert, self.mock_context)
        
        # Verify screenshot was taken
        mock_take_screenshot.assert_called_once_with(website)
        
        # Verify message and photo were sent
        self.mock_context.bot.send_message.assert_called_once()
        self.mock_context.bot.send_photo.assert_called_once()
        
        # Verify error pattern was matched
        message_text = self.mock_context.bot.send_message.call_args[1]['text']
        self.assertIn(pattern, message_text)
        self.assertIn(website, message_text)

    @patch('bot.get_zabbix_api')
    async def test_process_alerts_with_error_patterns(self, mock_zabbix_api):
        # Mock Zabbix API response
        mock_zapi = MagicMock()
        mock_zapi.trigger.get.return_value = [
            {
                'triggerid': '12345',
                'description': 'Test alert with Error: Connection refused',
                'priority': 3,
                'lastchange': str(int(time.time())),
                'hosts': [{'host': 'test-host'}]
            }
        ]
        mock_zabbix_api.return_value = mock_zapi
        
        # Add error pattern
        pattern = "Error: Connection refused"
        add_error_pattern(pattern, test_db)
        
        # Test process alerts
        alerts = [
            {
                'triggerid': '12345',
                'description': 'Test alert with Error: Connection refused',
                'priority': 3,
                'lastchange': str(int(time.time())),
                'hosts': [{'host': 'test-host'}]
            }
        ]
        await process_alerts_batch(alerts, self.mock_context)
        
        # Verify alert was saved with error pattern
        with get_db_connection(test_db) as conn:
            c = conn.cursor()
            c.execute('SELECT * FROM alerts WHERE trigger_id = ?', ('12345',))
            alert = c.fetchone()
            self.assertIsNotNone(alert)
            self.assertIn(pattern, alert['description'])

if __name__ == '__main__':
    unittest.main() 