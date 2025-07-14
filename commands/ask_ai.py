import os
import logging
import time
import requests
from telegram import Update
from telegram.ext import ContextTypes
from decorators import admin_only
from zabbix import get_zabbix_api
from config import Config

logger = logging.getLogger(__name__)

class AskAICommand:
    @admin_only
    async def execute(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text("Vui lòng nhập câu hỏi về dữ liệu Zabbix.")
            return

        try:
            zapi = get_zabbix_api()
            end_time = int(time.time())
            start_time = end_time - 86400 * 7  # 7 days

            alerts = zapi.trigger.get({
                "output": ["description", "lastchange", "priority"],
                "sortfield": "lastchange",
                "sortorder": "DESC",
                "time_from": start_time,
                "time_till": end_time
            })

            hosts = zapi.host.get({
                "output": ["host", "status"],
                "selectInterfaces": ["ip"]
            })

            prompt = f"""Dữ liệu Zabbix trong 7 ngày qua:
- Số lượng cảnh báo: {len(alerts)}
- Số lượng host: {len(hosts)}
- Thời gian: từ {time.strftime('%Y-%m-%d', time.localtime(start_time))} đến {time.strftime('%Y-%m-%d', time.localtime(end_time))}

Câu hỏi: {' '.join(context.args)}

Hãy phân tích dữ liệu và trả lời câu hỏi trên."""

            api_url = Config.OPENWEBUI_API_URL
            api_key = Config.OPENWEBUI_API_KEY

            if not api_url or not api_key:
                await update.message.reply_text("Chưa cấu hình Open WebUI API.")
                return

            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            data = {
                "model": "gpt-3.5-turbo",
                "messages": [
                    {"role": "user", "content": prompt}
                ]
            }

            await update.message.reply_text("Đang phân tích dữ liệu Zabbix...")
            
            response = requests.post(api_url, headers=headers, json=data, timeout=60)
            if response.status_code == 200:
                result = response.json()
                ai_reply = result.get('choices', [{}])[0].get('message', {}).get('content', 'Không nhận được phản hồi từ AI.')
                await update.message.reply_text(ai_reply)
            else:
                await update.message.reply_text(f"Lỗi từ AI: {response.text}")

        except Exception as e:
            logger.error(f"Lỗi khi phân tích dữ liệu: {str(e)}")
            await update.message.reply_text(f"Lỗi khi phân tích dữ liệu: {str(e)}")
