import os
import logging
import time
import io
import datetime
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from telegram import Update
from telegram.ext import ContextTypes
from zabbix import get_zabbix_api

logger = logging.getLogger(__name__)

ADMIN_IDS = [int(id) for id in os.getenv('ADMIN_IDS', '').split(',') if id]

class GetGraphCommand:
    async def execute(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id not in ADMIN_IDS:
            await update.message.reply_text("You don't have permission to use this command.")
            return

        if len(context.args) < 2:
            await update.message.reply_text("Please provide host and item key.\nExample: /graph host1 cpu.util")
            return

        host = context.args[0]
        item_key = context.args[1]
        period = int(context.args[2]) if len(context.args) > 2 else 3600  # Default 1 hour

        try:
            zapi = get_zabbix_api()
            hosts = zapi.host.get({
                "filter": {"host": host},
                "output": ["hostid"]
            })
            
            if not hosts:
                await update.message.reply_text(f"Host {host} not found")
                return

            hostid = hosts[0]["hostid"]

            items = zapi.item.get({
                "hostids": hostid,
                "search": {"key_": item_key},
                "output": ["itemid", "name"]
            })

            if not items:
                await update.message.reply_text(f"Item with key {item_key} not found")
                return

            itemid = items[0]["itemid"]
            item_name = items[0]["name"]

            time_till = int(time.time())
            time_from = time_till - period

            history = zapi.history.get({
                "itemids": itemid,
                "time_from": time_from,
                "time_till": time_till,
                "output": "extend",
                "sortfield": "clock",
                "sortorder": "ASC"
            })

            if not history:
                await update.message.reply_text("No historical data available")
                return

            plt.figure(figsize=(10, 6))
            times = [datetime.datetime.fromtimestamp(int(h["clock"])) for h in history]
            values = [float(h["value"]) for h in history]

            plt.plot(times, values)
            plt.title(f"{item_name} - {host}")
            plt.xlabel("Time")
            plt.ylabel("Value")
            plt.grid(True)
            plt.gcf().autofmt_xdate()
            plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))

            buf = io.BytesIO()
            plt.savefig(buf, format='png', bbox_inches='tight')
            buf.seek(0)
            plt.close()

            await update.message.reply_photo(photo=buf)
            
        except Exception as e:
            logger.error(f"Error creating graph: {str(e)}")
            await update.message.reply_text(f"Error creating graph: {str(e)}")
