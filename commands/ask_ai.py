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
            await update.message.reply_text("Vui lòng nhập tên host hoặc IP để phân tích.\nVí dụ: /ask server01 hoặc /ask 192.168.1.100")
            return

        try:
            search_term = ' '.join(context.args)
            await update.message.reply_text(f"Đang tìm kiếm host: {search_term}...")
            
            zapi = get_zabbix_api()
            host = self._find_host(zapi, search_term)
            
            if not host:
                await update.message.reply_text(f"Không tìm thấy host với tên hoặc IP: {search_term}")
                return

            await update.message.reply_text(f"Đang thu thập thông tin hệ thống cho host: {host['host']}...")
            
            # Lấy thông tin hệ thống
            system_info = self._get_system_info(zapi, host['hostid'])
            
            if not system_info:
                await update.message.reply_text(f"Không thể lấy thông tin hệ thống cho host: {host['host']}")
                return

            # Xây dựng prompt cho AI
            prompt = self._build_system_prompt(host, system_info)

            if not Config.OPENWEBUI_API_URL or not Config.OPENWEBUI_API_KEY:
                await update.message.reply_text("Open WebUI API chưa được cấu hình.")
                return

            await update.message.reply_text("Đang phân tích thông tin hệ thống với AI...")
            
            ai_response = self._call_ai_api(prompt)
            if ai_response:
                await update.message.reply_text(ai_response)
            else:
                await update.message.reply_text("Không thể kết nối đến AI service.")

        except Exception as e:
            logger.error(f"Error in AI analysis: {str(e)}")
            await update.message.reply_text(f"Lỗi khi phân tích dữ liệu: {str(e)}")

    def _find_host(self, zapi, search_term):
        """Tìm host theo tên hoặc IP"""
        # Tìm theo tên host
        hosts = zapi.host.get({
            "output": ["hostid", "host", "name", "status"],
            "selectInterfaces": ["ip"],
            "filter": {"host": [search_term]}
        })
        
        if hosts:
            return hosts[0]
        
        # Tìm theo IP
        hosts = zapi.host.get({
            "output": ["hostid", "host", "name", "status"],
            "selectInterfaces": ["ip"],
            "search": {"ip": search_term}
        })
        
        if hosts:
            return hosts[0]
        
        # Tìm theo tên hiển thị
        hosts = zapi.host.get({
            "output": ["hostid", "host", "name", "status"],
            "selectInterfaces": ["ip"],
            "search": {"name": search_term}
        })
        
        return hosts[0] if hosts else None

    def _get_system_info(self, zapi, hostid):
        """Lấy thông tin CPU, RAM, disk, network"""
        system_info = {
            'cpu': [],
            'memory': [],
            'disk': [],
            'network': []
        }
        
        # Lấy các item keys phổ biến cho monitoring
        item_keys = {
            'cpu': [
                'system.cpu.util[,user]',
                'system.cpu.util[,system]',
                'system.cpu.util[,iowait]',
                'system.cpu.util[,idle]',
                'system.cpu.load[percpu,avg1]',
                'system.cpu.load[percpu,avg5]',
                'system.cpu.load[percpu,avg15]'
            ],
            'memory': [
                'vm.memory.utilization',
                'vm.memory.size[available]',
                'vm.memory.size[total]',
                'vm.memory.size[used]',
                'vm.memory.size[free]',
                'vm.memory.size[cached]',
                'vm.memory.size[buffers]'
            ],
            'disk': [
                'vfs.fs.size[/,total]',
                'vfs.fs.size[/,used]',
                'vfs.fs.size[/,free]',
                'vfs.fs.size[/,pused]',
                'vfs.fs.inode[/,total]',
                'vfs.fs.inode[/,used]',
                'vfs.fs.inode[/,free]',
                'vfs.fs.inode[/,pused]'
            ],
            'network': [
                'net.if.in[*]',
                'net.if.out[*]',
                'net.if.total[*]',
                'net.if.in.dropped[*]',
                'net.if.out.dropped[*]',
                'net.if.in.errors[*]',
                'net.if.out.errors[*]'
            ]
        }
        
        # Lấy dữ liệu cho từng loại
        for category, keys in item_keys.items():
            for key in keys:
                items = zapi.item.get({
                    "output": ["itemid", "name", "key_", "lastvalue", "lastclock", "units"],
                    "hostids": [hostid],
                    "search": {"key_": key},
                    "sortfield": "lastclock",
                    "sortorder": "DESC",
                    "limit": 1
                })
                
                if items:
                    item = items[0]
                    system_info[category].append({
                        'name': item['name'],
                        'key': item['key_'],
                        'value': item['lastvalue'],
                        'units': item['units'],
                        'timestamp': item['lastclock']
                    })
        
        return system_info

    def _build_system_prompt(self, host, system_info):
        """Xây dựng prompt cho AI với thông tin hệ thống"""
        host_info = f"""
Thông tin Host:
- Tên: {host['host']}
- Tên hiển thị: {host['name']}
- Trạng thái: {'Hoạt động' if host['status'] == '0' else 'Không hoạt động'}
- IP: {host['interfaces'][0]['ip'] if host['interfaces'] else 'N/A'}
"""

        cpu_info = "CPU:\n"
        for item in system_info['cpu']:
            cpu_info += f"- {item['name']}: {item['value']} {item['units']}\n"

        memory_info = "Memory:\n"
        for item in system_info['memory']:
            memory_info += f"- {item['name']}: {item['value']} {item['units']}\n"

        disk_info = "Disk:\n"
        for item in system_info['disk']:
            disk_info += f"- {item['name']}: {item['value']} {item['units']}\n"

        network_info = "Network:\n"
        for item in system_info['network']:
            network_info += f"- {item['name']}: {item['value']} {item['units']}\n"

        prompt = f"""{host_info}

Thông tin hệ thống hiện tại:

{cpu_info}

{memory_info}

{disk_info}

{network_info}

Vui lòng phân tích thông tin hệ thống trên và đưa ra:
1. Đánh giá tổng quan về hiệu suất hệ thống
2. Các vấn đề tiềm ẩn cần chú ý
3. Khuyến nghị tối ưu hóa
4. Dự đoán xu hướng sử dụng tài nguyên

Trả lời bằng tiếng Việt với format rõ ràng, dễ đọc."""

        return prompt

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
            ],
            "max_tokens": 1000,
            "temperature": 0.7
        }

        try:
            response = requests.post(Config.OPENWEBUI_API_URL, headers=headers, json=data, timeout=60)
            if response.status_code == 200:
                result = response.json()
                return result.get('choices', [{}])[0].get('message', {}).get('content', 'Không nhận được phản hồi từ AI.')
            else:
                logger.error(f"AI API error: {response.status_code} - {response.text}")
                return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error: {str(e)}")
            return None
