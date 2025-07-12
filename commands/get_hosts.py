import os
import logging
from telegram import Update
from telegram.ext import ContextTypes
from zabbix import get_zabbix_api

logger = logging.getLogger(__name__)

ADMIN_IDS = [int(id) for id in os.getenv('ADMIN_IDS', '').split(',') if id]

class GetHostsCommand:
    async def execute(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id not in ADMIN_IDS:
            await update.message.reply_text("You don't have permission to use this command.")
            return

        try:
            zapi = get_zabbix_api()
            hosts = zapi.host.get({
                "output": ["host", "status"],
                "selectInterfaces": ["ip"]
            })
        except Exception as e:
            logger.error(f"Error fetching monitored hosts: {str(e)}")
            await update.message.reply_text(f"Error fetching monitored hosts: {str(e)}")
            return

        try:
            message = "List of hosts:\n\n"
            for host in hosts:
                status = "Online" if host['status'] == '0' else "Offline"
                ip = host['interfaces'][0]['ip'] if host['interfaces'] else "N/A"
                message += f"- {host['host']}\n"
                message += f"  IP: {ip}\n"
                message += f"  Status: {status}\n\n"

            await update.message.reply_text(message)
        except Exception as e:
            logger.error(f"Error processing host list: {str(e)}")
            await update.message.reply_text(f"Error getting host list: {str(e)}")
