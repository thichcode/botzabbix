import logging
from telegram import Update
from telegram.ext import ContextTypes
from decorators import admin_only
from zabbix import get_zabbix_api

logger = logging.getLogger(__name__)

class GetHostsCommand:
    @admin_only
    async def execute(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            zapi = get_zabbix_api()
            hosts = zapi.host.get({
                "output": ["host", "status"],
                "selectInterfaces": ["ip"]
            })

            if not hosts:
                await update.message.reply_text("Không có host nào được giám sát.")
                return

            message = "Danh sách các host:\n\n"
            for host in hosts:
                status = "Online" if host['status'] == '0' else "Offline"
                ip = host['interfaces'][0]['ip'] if host['interfaces'] else "N/A"
                message += f"- {host['host']}\n"
                message += f"  IP: {ip}\n"
                message += f"  Status: {status}\n\n"

            await update.message.reply_text(message)
        except Exception as e:
            logger.error(f"Error getting host list: {str(e)}")
            await update.message.reply_text(f"Lỗi khi lấy danh sách host: {str(e)}")
