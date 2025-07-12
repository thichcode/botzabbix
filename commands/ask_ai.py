import logging
import time
import requests
from telegram import Update
from telegram.ext import ContextTypes
from zabbix import get_zabbix_api
from decorators import admin_only, validate_input
from utils import retry, format_timestamp
from config import Config

logger = logging.getLogger(__name__)

class AskAiCommand:
    @admin_only
    @validate_input(max_length=500)
    async def execute(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text("Vui lòng nhập câu hỏi về dữ liệu Zabbix.")
            return

        try:
            await update.message.reply_text("Đang thu thập dữ liệu Zabbix...")
            
            end_time = int(time.time())
            start_time = end_time - 86400 * 7  # Last 7 days

            zapi = get_zabbix_api()
            alerts = self._fetch_alerts(zapi, start_time, end_time)
            hosts = self._fetch_hosts(zapi)

            if not alerts and not hosts:
                await update.message.reply_text("Không có dữ liệu Zabbix để phân tích.")
                return

            prompt = self._build_prompt(alerts, hosts, start_time, end_time, context.args)

            if not Config.OPENWEBUI_API_URL or not Config.OPENWEBUI_API_KEY:
                await update.message.reply_text("Open WebUI API chưa được cấu hình.")
                return

            await update.message.reply_text("Đang phân tích dữ liệu với AI...")
            
            ai_response = self._call_ai_api(prompt)
            if ai_response:
                await update.message.reply_text(ai_response)
            else:
                await update.message.reply_text("Không thể kết nối đến AI service.")

        except Exception as e:
            logger.error(f"Error in AI analysis: {str(e)}")
            await update.message.reply_text(f"Lỗi khi phân tích dữ liệu: {str(e)}")

    def _fetch_alerts(self, zapi, start_time, end_time):
        """Fetch alerts from Zabbix"""
        return zapi.trigger.get({
            "output": ["description", "lastchange", "priority"],
            "sortfield": "lastchange",
            "sortorder": "DESC",
            "time_from": start_time,
            "time_till": end_time
        })

    def _fetch_hosts(self, zapi):
        """Fetch hosts from Zabbix"""
        return zapi.host.get({
            "output": ["host", "status"],
            "selectInterfaces": ["ip"]
        })

    def _build_prompt(self, alerts, hosts, start_time, end_time, question_args):
        """Build AI prompt with Zabbix data"""
        return f"""Dữ liệu Zabbix trong 7 ngày qua:
- Số lượng cảnh báo: {len(alerts)}
- Số lượng hosts: {len(hosts)}
- Khoảng thời gian: từ {time.strftime('%Y-%m-%d', time.localtime(start_time))} đến {time.strftime('%Y-%m-%d', time.localtime(end_time))}

Câu hỏi: {' '.join(question_args)}

Vui lòng phân tích dữ liệu và trả lời câu hỏi trên bằng tiếng Việt."""

    def _call_ai_api(self, prompt):
        """Call AI API"""
        headers = {
            "Authorization": f"Bearer {Config.OPENWEBUI_API_KEY}",
            "Content-Type": "application/json"
        }
        data = {
            "model": "gpt-3.5-turbo",
            "messages": [
                {"role": "user", "content": prompt}
            ]
        }

        response = requests.post(Config.OPENWEBUI_API_URL, headers=headers, json=data, timeout=60)
        if response.status_code == 200:
            result = response.json()
            return result.get('choices', [{}])[0].get('message', {}).get('content', 'Không nhận được phản hồi từ AI.')
        else:
            logger.error(f"AI API error: {response.status_code} - {response.text}")
            return None
