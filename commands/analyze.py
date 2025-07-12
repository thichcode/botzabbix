import os
import logging
import time
from telegram import Update
from telegram.ext import ContextTypes
from zabbix import get_zabbix_api

logger = logging.getLogger(__name__)

ADMIN_IDS = [int(id) for id in os.getenv('ADMIN_IDS', '').split(',') if id]

class AnalyzeCommand:
    async def execute(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id not in ADMIN_IDS:
            await update.message.reply_text("You don't have permission to use this command.")
            return

        try:
            await update.message.reply_text("Analyzing and predicting alert trends...")
            zapi = get_zabbix_api()
            end_time = int(time.time())
            start_time = end_time - 86400 * 7  # 7 days

            triggers = zapi.trigger.get({
                "output": ["description", "lastchange", "priority"],
                "selectHosts": ["host"],
                "sortfield": "lastchange",
                "sortorder": "DESC",
                "time_from": start_time,
                "time_till": end_time
            })

            if not triggers:
                await update.message.reply_text("No alert data available for the past 7 days to analyze.")
                return

            patterns = {}
            host_alerts = {}
            daily_counts = {}
            for trigger in triggers:
                desc = trigger['description']
                host = trigger['hosts'][0]['host'] if trigger['hosts'] else "Unknown"
                timestamp = int(trigger['lastchange'])
                day = time.strftime('%Y-%m-%d', time.localtime(timestamp))
                
                if desc in patterns:
                    patterns[desc] += 1
                else:
                    patterns[desc] = 1
                    
                if host in host_alerts:
                    host_alerts[host] += 1
                else:
                    host_alerts[host] = 1
                    
                if day in daily_counts:
                    daily_counts[day] += 1
                else:
                    daily_counts[day] = 1

            report = "📊 Analysis and Trend Prediction Report (Past 7 Days):\n\n"
            report += f"Total Alerts: {len(triggers)}\n\n"
            
            report += "🔥 Most Frequent Alerts:\n"
            sorted_patterns = sorted(patterns.items(), key=lambda x: x[1], reverse=True)[:5]
            for desc, count in sorted_patterns:
                report += f"- {desc}: {count} times\n"
            report += "\n"
            
            report += "🖥️ Hosts with Most Alerts:\n"
            sorted_hosts = sorted(host_alerts.items(), key=lambda x: x[1], reverse=True)[:5]
            for host, count in sorted_hosts:
                report += f"- {host}: {count} alerts\n"
            report += "\n"
            
            report += "📅 Alert Trends by Day:\n"
            sorted_days = sorted(daily_counts.items(), key=lambda x: x[0])
            for day, count in sorted_days:
                report += f"- {day}: {count} alerts\n"
            report += "\n"
            
            report += "🔮 Predictions:\n"
            if sorted_patterns:
                most_frequent = sorted_patterns[0]
                report += f"- Alert '{most_frequent[0]}' is likely to occur next due to high frequency ({most_frequent[1]} times).\n"
            if sorted_hosts:
                most_affected = sorted_hosts[0]
                report += f"- Host '{most_affected[0]}' is likely to have issues next ({most_affected[1]} alerts).\n"
            
            await update.message.reply_text(report)
            
        except Exception as e:
            logger.error(f"Error in analyze_and_predict: {str(e)}")
            await update.message.reply_text(f"Error analyzing and predicting trends: {str(e)}")
