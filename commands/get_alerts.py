import logging
from telegram import Update
from telegram.ext import ContextTypes
from zabbix import get_zabbix_api
from db import save_alert
from screenshot import send_alert_with_screenshot
from decorators import admin_only
from utils import retry, format_timestamp

logger = logging.getLogger(__name__)

class GetAlertsCommand:
    @admin_only
    async def execute(self, update: Update, context: ContextTypes.DEFAULT_TYPE):

        try:
            await update.message.reply_text("Đang lấy cảnh báo mới nhất...")
            
            zapi = get_zabbix_api()
            alerts = self._fetch_alerts(zapi)
            
            if not alerts:
                await update.message.reply_text("Không có cảnh báo mới nào.")
                return
                
            await update.message.reply_text(f"Tìm thấy {len(alerts)} cảnh báo mới nhất:")
            
            # Process each alert
            for alert in alerts:
                await self._process_alert(alert, update.effective_chat.id, context)
                
        except Exception as e:
            logger.error(f"Error fetching latest alerts: {str(e)}")
            await update.message.reply_text(f"Lỗi khi lấy cảnh báo: {str(e)}")
            return

    def _fetch_alerts(self, zapi):
        """Fetch alerts from Zabbix"""
        return zapi.trigger.get({
            "output": ["description", "lastchange", "priority", "triggerid"],
            "selectHosts": ["host"],
            "sortfield": "lastchange",
            "sortorder": "DESC",
            "limit": 10
        })

    async def _process_alert(self, alert, chat_id, context):
        """Process individual alert"""
        host = alert['hosts'][0]['host'] if alert['hosts'] else "Unknown"
        alert_info = {
            'trigger_id': alert['triggerid'],
            'host': host,
            'description': alert['description'],
            'priority': alert['priority'],
            'timestamp': int(alert['lastchange'])
        }
        
        # Save to database
        save_alert(
            alert_info['trigger_id'],
            alert_info['host'],
            alert_info['description'],
            alert_info['priority'],
            alert_info['timestamp']
        )
        
        # Send with screenshot
        await send_alert_with_screenshot(chat_id, alert_info, context)
