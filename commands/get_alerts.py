import logging
import time
import io
from telegram import Update
from telegram.ext import ContextTypes
from decorators import admin_only
from zabbix import get_zabbix_api
from db import save_alert
from utils import extract_url_from_text
from screenshot import take_screenshot

logger = logging.getLogger(__name__)

class GetAlertsCommand:
    @admin_only
    async def execute(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            zapi = get_zabbix_api()
            alerts = zapi.trigger.get({
                "output": ["description", "lastchange", "priority", "triggerid"],
                "selectHosts": ["host"],
                "sortfield": "lastchange",
                "sortorder": "DESC",
                "limit": 10
            })

            if not alerts:
                await update.message.reply_text("Không có cảnh báo nào.")
                return

            for alert in alerts:
                host = alert['hosts'][0]['host'] if alert['hosts'] else "Unknown"
                alert_info = {
                    'trigger_id': alert['triggerid'],
                    'host': host,
                    'description': alert['description'],
                    'priority': alert['priority'],
                    'timestamp': int(alert['lastchange'])
                }
                
                save_alert(
                    alert_info['trigger_id'],
                    alert_info['host'],
                    alert_info['description'],
                    alert_info['priority'],
                    alert_info['timestamp']
                )
                
                await self.send_alert_with_screenshot(update.effective_chat.id, alert_info, context)

        except Exception as e:
            logger.error(f"Error getting alerts: {str(e)}")
            await update.message.reply_text(f"Lỗi khi lấy cảnh báo: {str(e)}")

    async def send_alert_with_screenshot(self, chat_id: int, alert_info: dict, context: ContextTypes.DEFAULT_TYPE):
        """Gửi cảnh báo kèm ảnh chụp màn hình nếu có URL trong trigger"""
        try:
            message = f"⚠️ Cảnh báo mới:\n"
            message += f"Host: {alert_info['host']}\n"
            message += f"Mô tả: {alert_info['description']}\n"
            message += f"Mức độ: {alert_info['priority']}\n"
            message += f"Thời gian: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(alert_info['timestamp']))}\n"

            await context.bot.send_message(chat_id=chat_id, text=message)

            url = extract_url_from_text(alert_info['description'])
            if url:
                await context.bot.send_message(chat_id=chat_id, text=f"Đang chụp ảnh website {url}...")
                try:
                    screenshot = await take_screenshot(url)
                    await context.bot.send_photo(chat_id=chat_id, photo=io.BytesIO(screenshot))
                except Exception as e:
                    logger.error(f"Error taking screenshot for alert: {e}")
                    await context.bot.send_message(chat_id=chat_id, text="Không thể chụp ảnh website.")

        except Exception as e:
            logger.error(f"Error sending alert with screenshot: {e}")
