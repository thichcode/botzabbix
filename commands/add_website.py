import logging
from telegram import Update
from telegram.ext import ContextTypes
from decorators import admin_only
from db import add_host_website

logger = logging.getLogger(__name__)

class AddWebsiteCommand:
    @admin_only
    async def execute(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if len(context.args) < 2:
            await update.message.reply_text("Vui lòng cung cấp host và URL website.\nVí dụ: /addwebsite host1 https://example.com")
            return

        host = context.args[0]
        url = context.args[1]
        enabled = True if len(context.args) < 3 else context.args[2].lower() == 'true'

        if add_host_website(host, url, enabled):
            await update.message.reply_text(f"Đã thêm website {url} cho host {host}")
        else:
            await update.message.reply_text(f"Lỗi khi thêm website.")
