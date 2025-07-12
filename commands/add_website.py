import os
import logging
import sqlite3
from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

ADMIN_IDS = [int(id) for id in os.getenv('ADMIN_IDS', '').split(',') if id]

class AddWebsiteCommand:
    async def execute(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id not in ADMIN_IDS:
            await update.message.reply_text("You don't have permission to use this command.")
            return

        if len(context.args) < 2:
            await update.message.reply_text("Please provide host and URL website.\nExample: /addwebsite host1 https://example.com")
            return

        host = context.args[0]
        url = context.args[1]
        enabled = True if len(context.args) < 3 else context.args[2].lower() == 'true'

        try:
            conn = sqlite3.connect('zabbix_alerts.db')
            c = conn.cursor()
            
            c.execute('''INSERT OR REPLACE INTO host_websites (host, website_url, screenshot_enabled)
                         VALUES (?, ?, ?)''', (host, url, enabled))
            
            conn.commit()
            conn.close()
            
            await update.message.reply_text(f"Added website {url} for host {host}")
        except Exception as e:
            logger.error(f"Error inserting host website: {str(e)}")
            await update.message.reply_text(f"Error adding website: {str(e)}")
