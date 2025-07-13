import os
import logging
import time
import io
import datetime
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from zabbix import get_zabbix_api
from decorators import admin_only
from utils import format_timestamp

logger = logging.getLogger(__name__)

ADMIN_IDS = [int(id) for id in os.getenv('ADMIN_IDS', '').split(',') if id]

class GetGraphCommand:
    @admin_only
    async def execute(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text(
                "Vui lòng nhập tên host hoặc IP để tìm kiếm.\n"
                "Ví dụ: /graph server01 hoặc /graph 192.168.1.100"
            )
            return

        search_term = ' '.join(context.args)
        
        try:
            await update.message.reply_text(f"Đang tìm kiếm host: {search_term}...")
            
            zapi = get_zabbix_api()
            host = self._find_host(zapi, search_term)
            
            if not host:
                await update.message.reply_text(f"Không tìm thấy host với tên hoặc IP: {search_term}")
                return

            await update.message.reply_text(f"Đang tìm kiếm items cho host: {host['host']}...")
            
            # Lấy danh sách items phổ biến
            items = self._get_common_items(zapi, host['hostid'])
            
            if not items:
                await update.message.reply_text(f"Không tìm thấy items nào cho host: {host['host']}")
                return

            # Tạo gợi ý cho user
            await self._show_item_suggestions(update, host, items)
            
        except Exception as e:
            logger.error(f"Error in get_graph: {str(e)}")
            await update.message.reply_text(f"Lỗi khi tìm kiếm: {str(e)}")

    def _find_host(self, zapi, search_term):
        """Tìm host theo tên hoặc IP"""
        # Tìm theo tên host chính xác
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
        
        if hosts:
            return hosts[0]
        
        # Tìm gần đúng (fuzzy search)
        hosts = zapi.host.get({
            "output": ["hostid", "host", "name", "status"],
            "selectInterfaces": ["ip"],
            "search": {"host": search_term}
        })
        
        return hosts[0] if hosts else None

    def _get_common_items(self, zapi, hostid):
        """Lấy danh sách items phổ biến cho monitoring"""
        common_item_keys = [
            # CPU
            'system.cpu.util[,user]',
            'system.cpu.util[,system]',
            'system.cpu.util[,iowait]',
            'system.cpu.util[,idle]',
            'system.cpu.load[percpu,avg1]',
            'system.cpu.load[percpu,avg5]',
            'system.cpu.load[percpu,avg15]',
            
            # Memory
            'vm.memory.utilization',
            'vm.memory.size[available]',
            'vm.memory.size[total]',
            'vm.memory.size[used]',
            'vm.memory.size[free]',
            
            # Disk
            'vfs.fs.size[/,total]',
            'vfs.fs.size[/,used]',
            'vfs.fs.size[/,free]',
            'vfs.fs.size[/,pused]',
            'vfs.fs.inode[/,total]',
            'vfs.fs.inode[/,used]',
            'vfs.fs.inode[/,free]',
            
            # Network
            'net.if.in[*]',
            'net.if.out[*]',
            'net.if.total[*]',
            'net.if.in.dropped[*]',
            'net.if.out.dropped[*]',
            'net.if.in.errors[*]',
            'net.if.out.errors[*]',
            
            # System
            'system.uptime',
            'system.localtime',
            'system.swap.size[,total]',
            'system.swap.size[,free]',
            'system.swap.size[,used]',
            
            # Processes
            'proc.num[]',
            'proc.num[,,run]',
            'proc.num[,,sleep]',
            'proc.num[,,zombie]',
            
            # Services
            'net.tcp.port[,80]',
            'net.tcp.port[,443]',
            'net.tcp.port[,22]',
            'net.tcp.port[,3306]',
            'net.tcp.port[,5432]'
        ]
        
        items = []
        for key in common_item_keys:
            found_items = zapi.item.get({
                "hostids": [hostid],
                "search": {"key_": key},
                "output": ["itemid", "name", "key_", "units", "lastvalue", "lastclock"],
                "sortfield": "name",
                "limit": 1
            })
            
            if found_items:
                items.append(found_items[0])
        
        return items

    async def _show_item_suggestions(self, update, host, items):
        """Hiển thị gợi ý items cho user"""
        host_info = f"🖥️ **Host:** {host['host']}\n"
        if host['name'] != host['host']:
            host_info += f"📝 **Tên hiển thị:** {host['name']}\n"
        host_info += f"🌐 **IP:** {host['interfaces'][0]['ip'] if host['interfaces'] else 'N/A'}\n"
        host_info += f"📊 **Tìm thấy {len(items)} items phổ biến**\n\n"
        
        # Nhóm items theo category
        categories = {
            'CPU': [],
            'Memory': [],
            'Disk': [],
            'Network': [],
            'System': [],
            'Processes': [],
            'Services': []
        }
        
        for item in items:
            key = item['key_']
            if 'cpu' in key.lower():
                categories['CPU'].append(item)
            elif 'memory' in key.lower() or 'vm.memory' in key:
                categories['Memory'].append(item)
            elif 'fs.size' in key or 'fs.inode' in key:
                categories['Disk'].append(item)
            elif 'net.if' in key or 'net.tcp' in key:
                categories['Network'].append(item)
            elif 'proc' in key:
                categories['Processes'].append(item)
            elif 'system.' in key and 'cpu' not in key:
                categories['System'].append(item)
            else:
                categories['Services'].append(item)
        
        # Tạo message với gợi ý
        message = host_info
        message += "**Chọn item để xem biểu đồ:**\n\n"
        
        # Hiển thị từng category
        for category, category_items in categories.items():
            if category_items:
                message += f"**{category}:**\n"
                for i, item in enumerate(category_items[:3], 1):  # Giới hạn 3 items mỗi category
                    last_value = item.get('lastvalue', 'N/A')
                    units = item.get('units', '')
                    if units:
                        last_value += f" {units}"
                    
                    message += f"{i}. {item['name']}\n"
                    message += f"   📊 Giá trị hiện tại: {last_value}\n"
                    message += f"   🔗 Key: `{item['key_']}`\n\n"
        
        # Tạo inline keyboard cho các lựa chọn nhanh
        keyboard = []
        row = []
        
        # Thêm các nút cho CPU, Memory, Disk, Network
        quick_items = [
            ('CPU', 'system.cpu.util[,user]'),
            ('Memory', 'vm.memory.utilization'),
            ('Disk', 'vfs.fs.size[/,pused]'),
            ('Network', 'net.if.in[*]')
        ]
        
        for label, key in quick_items:
            # Tìm item tương ứng
            matching_items = [item for item in items if key in item['key_']]
            if matching_items:
                item = matching_items[0]
                callback_data = f"graph_{host['hostid']}_{item['itemid']}_3600"  # 1 hour default
                row.append(InlineKeyboardButton(f"📈 {label}", callback_data=callback_data))
                
                if len(row) == 2:
                    keyboard.append(row)
                    row = []
        
        if row:
            keyboard.append(row)
        
        # Thêm nút tìm kiếm thêm
        keyboard.append([InlineKeyboardButton("🔍 Tìm kiếm thêm items", callback_data=f"search_items_{host['hostid']}")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            message,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

    async def create_graph(self, update, hostid, itemid, period=3600):
        """Tạo biểu đồ cho item cụ thể"""
        try:
            zapi = get_zabbix_api()
            
            # Lấy thông tin item
            items = zapi.item.get({
                "itemids": [itemid],
                "output": ["name", "units", "hostid"]
            })
            
            if not items:
                await update.message.reply_text("Không tìm thấy item")
                return
            
            item = items[0]
            
            # Lấy thông tin host
            hosts = zapi.host.get({
                "hostids": [item['hostid']],
                "output": ["host"]
            })
            
            host_name = hosts[0]['host'] if hosts else "Unknown"
            
            # Lấy dữ liệu lịch sử
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
                await update.message.reply_text("Không có dữ liệu lịch sử cho item này")
                return
            
            # Tạo biểu đồ
            plt.figure(figsize=(12, 8))
            times = [datetime.datetime.fromtimestamp(int(h["clock"])) for h in history]
            values = [float(h["value"]) for h in history]
            
            plt.plot(times, values, linewidth=2, color='#2E86AB')
            plt.title(f"{item['name']} - {host_name}", fontsize=14, fontweight='bold')
            plt.xlabel("Thời gian", fontsize=12)
            plt.ylabel(f"Giá trị ({item['units']})" if item['units'] else "Giá trị", fontsize=12)
            plt.grid(True, alpha=0.3)
            plt.gcf().autofmt_xdate()
            
            # Format trục thời gian
            if period <= 3600:  # 1 giờ
                plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
            elif period <= 86400:  # 1 ngày
                plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
            else:  # Nhiều ngày
                plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%m-%d %H:%M'))
            
            # Thêm thông tin
            current_value = values[-1] if values else 0
            avg_value = sum(values) / len(values) if values else 0
            max_value = max(values) if values else 0
            min_value = min(values) if values else 0
            
            info_text = f"Hiện tại: {current_value:.2f}\nTrung bình: {avg_value:.2f}\nMax: {max_value:.2f}\nMin: {min_value:.2f}"
            plt.figtext(0.02, 0.02, info_text, fontsize=10, bbox=dict(boxstyle="round,pad=0.3", facecolor="lightgray", alpha=0.8))
            
            buf = io.BytesIO()
            plt.savefig(buf, format='png', bbox_inches='tight', dpi=150)
            buf.seek(0)
            plt.close()
            
            # Tạo caption
            period_text = "1 giờ" if period == 3600 else f"{period//3600} giờ" if period < 86400 else f"{period//86400} ngày"
            caption = f"📊 **{item['name']}**\n🖥️ Host: {host_name}\n⏰ Khoảng thời gian: {period_text}\n📈 Số điểm dữ liệu: {len(history)}"
            
            await update.message.reply_photo(
                photo=buf,
                caption=caption,
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Error creating graph: {str(e)}")
            await update.message.reply_text(f"Lỗi khi tạo biểu đồ: {str(e)}")
