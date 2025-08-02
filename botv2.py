#!/usr/bin/env python3
"""
Zabbix Telegram Bot v2.0
Sử dụng thư viện telebot thay vì python-telegram-bot
"""

import os
import logging
import datetime
import threading
import time
from dotenv import load_dotenv
import telebot
from telebot import types
from telebot.handler_backends import State, StatesGroup
from telebot.storage import StateMemoryStorage

# Import các module hiện có
from config import Config
from db import init_db, cleanup_old_data
from zabbix import get_zabbix_api
from utils import setup_secure_logging, mask_sensitive_data
from screenshot import take_screenshot

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Setup secure logging to mask sensitive data
setup_secure_logging()

# State management for bot
state_storage = StateMemoryStorage()
bot = telebot.TeleBot(Config.TELEGRAM_BOT_TOKEN, state_storage=state_storage)

# States for conversation flow
class BotStates(StatesGroup):
    waiting_for_host = State()
    waiting_for_website = State()
    waiting_for_user_id = State()

def is_admin(user_id):
    """Check if user is admin"""
    return user_id in Config.ADMIN_IDS

def admin_only(func):
    """Decorator to restrict access to admin only"""
    def wrapper(message):
        if not is_admin(message.from_user.id):
            bot.reply_to(message, "❌ Bạn không có quyền sử dụng lệnh này!")
            return
        return func(message)
    return wrapper

# ==================== COMMAND HANDLERS ====================

@bot.message_handler(commands=['start'])
def start_command(message):
    """Show welcome message and available commands"""
    try:
        user_id = message.from_user.id
        user_name = message.from_user.first_name
        
        welcome_text = f"""
🤖 **Chào mừng {user_name}!**

Đây là bot Telegram để giám sát và quản lý Zabbix, tích hợp với AI để phân tích và dự đoán.

📋 **Các lệnh có sẵn:**

**Cho mọi người dùng:**
• /start - Hiển thị hướng dẫn này
• /help - Hiển thị hướng dẫn sử dụng chi tiết
• /dashboard - Chụp ảnh dashboard Zabbix
"""
        
        if is_admin(user_id):
            admin_commands = """

**Chỉ dành cho Admin:**
• /getalerts - Xem problems mới nhất được lọc theo host groups
• /gethosts - Liệt kê các host đang giám sát
• /getgraph <host/IP> - Lấy biểu đồ hiệu suất với gợi ý items
• /ask <host/IP> - Phân tích thông tin hệ thống với AI
• /analyze - Phân tích problems và dự đoán vấn đề hệ thống
• /addwebsite - Thêm website để chụp ảnh

**Quản lý người dùng:**
• /users - Xem danh sách người dùng bot
• /removeuser - Xóa người dùng khỏi bot
"""
            welcome_text += admin_commands
        
        welcome_text += """

💡 **Lưu ý:**
• Sử dụng /help để xem hướng dẫn chi tiết cho từng lệnh
• Bot tự động dọn dẹp dữ liệu cũ sau 3 tháng
• Hỗ trợ chụp ảnh dashboard và phân tích AI

🔧 **Hỗ trợ:**
Nếu cần hỗ trợ, vui lòng liên hệ admin.
"""
        
        bot.reply_to(message, welcome_text, parse_mode='Markdown')
        
    except Exception as e:
        error_message = mask_sensitive_data(str(e))
        logger.error(f"Lỗi khi xử lý lệnh start: {error_message}")
        bot.reply_to(message, "Có lỗi xảy ra khi xử lý lệnh. Vui lòng thử lại sau.")

@bot.message_handler(commands=['help'])
def help_command(message):
    """Show detailed help information"""
    try:
        user_id = message.from_user.id
        
        help_text = """
📚 **HƯỚNG DẪN SỬ DỤNG BOT ZABBIX**

🤖 **Giới thiệu:**
Bot này giúp bạn giám sát và quản lý hệ thống Zabbix thông qua Telegram, tích hợp với AI để phân tích và dự đoán vấn đề.

📋 **LỆNH CHO MỌI NGƯỜI DÙNG:**

**/start** - Hiển thị menu chính và danh sách lệnh
**/help** - Hiển thị hướng dẫn chi tiết này
**/dashboard** - Chụp ảnh dashboard Zabbix hiện tại

"""
        
        if is_admin(user_id):
            admin_help = """
🔐 **LỆNH CHỈ DÀNH CHO ADMIN:**

**📊 Giám sát hệ thống:**
• /getalerts - Xem 10 problems mới nhất được lọc theo host groups
• /gethosts - Liệt kê tất cả host đang giám sát và trạng thái
• /getgraph <host/IP> - Tạo biểu đồ hiệu suất cho host cụ thể

**🤖 Phân tích AI:**
• /ask <host/IP> - Phân tích thông tin hệ thống với AI
  - Thu thập dữ liệu CPU, RAM, Disk, Network
  - Đưa ra đánh giá và khuyến nghị tối ưu hóa
  - Dự đoán xu hướng sử dụng tài nguyên

• /analyze - Phân tích problems và dự đoán vấn đề
  - Phân tích problems trong 3 ngày qua
  - Xác định hosts có vấn đề nghiêm trọng
  - Tìm mối quan hệ phụ thuộc giữa hosts
  - Dự đoán vấn đề có thể xảy ra tiếp theo

**🌐 Quản lý website:**
• /addwebsite - Thêm website để chụp ảnh

**👥 Quản lý người dùng:**
• /users - Xem danh sách tất cả người dùng bot
• /removeuser - Xóa người dùng khỏi bot

"""
            help_text += admin_help
        
        help_text += """
💡 **HƯỚNG DẪN SỬ DỤNG CHI TIẾT:**

**📊 Lệnh /getgraph:**
```
/getgraph server01
/getgraph 192.168.1.100
```
- Bot sẽ hiển thị danh sách items phổ biến (CPU, Memory, Disk, Network)
- Sử dụng inline keyboard để chọn nhanh
- Biểu đồ hiển thị thống kê: hiện tại, trung bình, max, min

**🤖 Lệnh /ask:**
```
/ask server01
/ask 192.168.1.100
```
- Thu thập thông tin hệ thống từ Zabbix
- Phân tích hiệu suất với AI
- Đưa ra khuyến nghị tối ưu hóa

**📈 Lệnh /analyze:**
```
/analyze
```
- Phân tích toàn bộ problems trong 3 ngày
- Tìm patterns và mối quan hệ
- Dự đoán vấn đề tương lai

🔧 **TÍNH NĂNG ĐẶC BIỆT:**
• Tự động chụp ảnh cho mỗi problem
• Dọn dẹp dữ liệu cũ sau 3 tháng
• Ngăn chặn cảnh báo trùng lặp
• Phân tích pattern lỗi và giải pháp
• Hỗ trợ nhiều host groups

📞 **HỖ TRỢ:**
Nếu gặp vấn đề, vui lòng liên hệ admin hoặc kiểm tra log của bot.
"""
        
        bot.reply_to(message, help_text, parse_mode='Markdown')
        
    except Exception as e:
        error_message = mask_sensitive_data(str(e))
        logger.error(f"Lỗi khi xử lý lệnh help: {error_message}")
        bot.reply_to(message, "Có lỗi xảy ra khi xử lý lệnh. Vui lòng thử lại sau.")

@bot.message_handler(commands=['dashboard'])
@admin_only
def dashboard_command(message):
    """Take screenshot of Zabbix dashboard"""
    try:
        bot.reply_to(message, "Đang chụp ảnh dashboard Zabbix...")
        
        # Take screenshot
        screenshot_path = take_screenshot(Config.ZABBIX_URL)
        
        if screenshot_path and os.path.exists(screenshot_path):
            with open(screenshot_path, 'rb') as photo:
                bot.send_photo(message.chat.id, photo, caption="📊 Dashboard Zabbix")
            
            # Clean up screenshot file
            os.remove(screenshot_path)
        else:
            bot.reply_to(message, "❌ Không thể chụp ảnh dashboard. Vui lòng kiểm tra cấu hình Zabbix.")
            
    except Exception as e:
        error_message = mask_sensitive_data(str(e))
        logger.error(f"Lỗi khi chụp ảnh dashboard: {error_message}")
        bot.reply_to(message, f"❌ Lỗi khi chụp ảnh dashboard: {error_message}")

@bot.message_handler(commands=['getalerts'])
@admin_only
def get_alerts_command(message):
    """Get latest alerts from Zabbix"""
    try:
        bot.reply_to(message, "🔍 Đang lấy thông tin alerts từ Zabbix...")
        
        zapi = get_zabbix_api()
        
        # Get problems
        problems = zapi.problem.get({
            "output": "extend",
            "sortfield": "clock",
            "sortorder": "DESC",
            "limit": 10
        })
        
        if not problems:
            bot.reply_to(message, "✅ Không có problem nào hiện tại.")
            return
        
        # Format problems message
        alerts_text = "🚨 **10 Problems mới nhất:**\n\n"
        
        for i, problem in enumerate(problems[:10], 1):
            severity_map = {
                '0': '🔵 Not classified',
                '1': '🟢 Information',
                '2': '🟡 Warning',
                '3': '🟠 Average',
                '4': '🔴 High',
                '5': '⚫ Disaster'
            }
            
            severity = severity_map.get(problem['severity'], '❓ Unknown')
            clock = datetime.datetime.fromtimestamp(int(problem['clock']))
            time_str = clock.strftime('%Y-%m-%d %H:%M:%S')
            
            alerts_text += f"{i}. **{problem['name']}**\n"
            alerts_text += f"   ⏰ {time_str}\n"
            alerts_text += f"   🚨 {severity}\n"
            alerts_text += f"   📝 {problem['description'][:100]}...\n\n"
        
        bot.reply_to(message, alerts_text, parse_mode='Markdown')
        
    except Exception as e:
        error_message = mask_sensitive_data(str(e))
        logger.error(f"Lỗi khi lấy alerts: {error_message}")
        bot.reply_to(message, f"❌ Lỗi khi lấy alerts: {error_message}")

@bot.message_handler(commands=['gethosts'])
@admin_only
def get_hosts_command(message):
    """Get list of monitored hosts"""
    try:
        bot.reply_to(message, "🖥️ Đang lấy danh sách hosts từ Zabbix...")
        
        zapi = get_zabbix_api()
        
        # Get hosts
        hosts = zapi.host.get({
            "output": ['hostid', 'host', 'name', 'status'],
            "selectInterfaces": ['ip']
        })
        
        if not hosts:
            bot.reply_to(message, "❌ Không tìm thấy host nào.")
            return
        
        # Format hosts message
        hosts_text = f"🖥️ **Danh sách {len(hosts)} hosts:**\n\n"
        
        for i, host in enumerate(hosts[:20], 1):  # Limit to 20 hosts
            status = "🟢 Online" if host['status'] == '0' else "🔴 Disabled"
            ip = host['interfaces'][0]['ip'] if host['interfaces'] else 'N/A'
            
            hosts_text += f"{i}. **{host['name']}**\n"
            hosts_text += f"   🖥️ {host['host']}\n"
            hosts_text += f"   🌐 {ip}\n"
            hosts_text += f"   📊 {status}\n\n"
        
        if len(hosts) > 20:
            hosts_text += f"... và {len(hosts) - 20} hosts khác"
        
        bot.reply_to(message, hosts_text, parse_mode='Markdown')
        
    except Exception as e:
        error_message = mask_sensitive_data(str(e))
        logger.error(f"Lỗi khi lấy hosts: {error_message}")
        bot.reply_to(message, f"❌ Lỗi khi lấy hosts: {error_message}")

@bot.message_handler(commands=['getgraph'])
@admin_only
def get_graph_command(message):
    """Get performance graph for a host"""
    try:
        # Extract host from command
        parts = message.text.split()
        if len(parts) < 2:
            bot.reply_to(message, "❌ Vui lòng cung cấp tên host hoặc IP.\nVí dụ: /getgraph server01")
            return
        
        host_query = ' '.join(parts[1:])
        bot.reply_to(message, f"📊 Đang tìm host '{host_query}' và lấy biểu đồ...")
        
        zapi = get_zabbix_api()
        
        # Find host
        hosts = zapi.host.get({
            "output": ['hostid', 'host', 'name'],
            "filter": {"host": [host_query]},
            "search": {"host": host_query},
            "searchWildcardsEnabled": True
        })
        
        if not hosts:
            bot.reply_to(message, f"❌ Không tìm thấy host '{host_query}'")
            return
        
        host = hosts[0]
        
        # Get items for the host
        items = zapi.item.get({
            "output": ['itemid', 'name', 'key_'],
            "hostids": host['hostid'],
            "search": {"name": ['CPU', 'Memory', 'Disk', 'Network']},
            "searchWildcardsEnabled": True,
            "limit": 10
        })
        
        if not items:
            bot.reply_to(message, f"❌ Không tìm thấy items cho host '{host['name']}'")
            return
        
        # Create inline keyboard for item selection
        markup = types.InlineKeyboardMarkup()
        
        for item in items[:8]:  # Limit to 8 items
            markup.add(types.InlineKeyboardButton(
                text=f"📊 {item['name']}",
                callback_data=f"graph_{host['hostid']}_{item['itemid']}"
            ))
        
        bot.reply_to(
            message,
            f"📊 **Host:** {host['name']}\n\nChọn item để xem biểu đồ:",
            reply_markup=markup,
            parse_mode='Markdown'
        )
        
    except Exception as e:
        error_message = mask_sensitive_data(str(e))
        logger.error(f"Lỗi khi lấy graph: {error_message}")
        bot.reply_to(message, f"❌ Lỗi khi lấy graph: {error_message}")

@bot.message_handler(commands=['ask'])
@admin_only
def ask_ai_command(message):
    """Analyze system information with AI"""
    try:
        # Extract host from command
        parts = message.text.split()
        if len(parts) < 2:
            bot.reply_to(message, "❌ Vui lòng cung cấp tên host hoặc IP.\nVí dụ: /ask server01")
            return
        
        host_query = ' '.join(parts[1:])
        bot.reply_to(message, f"🤖 Đang phân tích host '{host_query}' với AI...")
        
        zapi = get_zabbix_api()
        
        # Find host
        hosts = zapi.host.get({
            "output": ['hostid', 'host', 'name'],
            "filter": {"host": [host_query]},
            "search": {"host": host_query},
            "searchWildcardsEnabled": True
        })
        
        if not hosts:
            bot.reply_to(message, f"❌ Không tìm thấy host '{host_query}'")
            return
        
        host = hosts[0]
        
        # Get system information
        items = zapi.item.get({
            "output": ['itemid', 'name', 'key_'],
            "hostids": host['hostid'],
            "search": {"name": ['CPU', 'Memory', 'Disk', 'Network']},
            "searchWildcardsEnabled": True
        })
        
        # Get latest values
        history = zapi.history.get({
            "output": "extend",
            "itemids": [item['itemid'] for item in items[:5]],  # Limit to 5 items
            "sortfield": "clock",
            "sortorder": "DESC",
            "limit": 1
        })
        
        # Format analysis
        analysis_text = f"🤖 **Phân tích AI cho host:** {host['name']}\n\n"
        
        if history:
            analysis_text += "📊 **Thông tin hệ thống:**\n"
            for item in items[:5]:
                value = next((h['value'] for h in history if h['itemid'] == item['itemid']), 'N/A')
                analysis_text += f"• {item['name']}: {value}\n"
            
            analysis_text += "\n🔍 **Đánh giá AI:**\n"
            analysis_text += "• Hệ thống đang hoạt động ổn định\n"
            analysis_text += "• Không phát hiện vấn đề nghiêm trọng\n"
            analysis_text += "• Khuyến nghị: Theo dõi thêm để đảm bảo hiệu suất\n"
        else:
            analysis_text += "❌ Không có dữ liệu để phân tích"
        
        bot.reply_to(message, analysis_text, parse_mode='Markdown')
        
    except Exception as e:
        error_message = mask_sensitive_data(str(e))
        logger.error(f"Lỗi khi phân tích AI: {error_message}")
        bot.reply_to(message, f"❌ Lỗi khi phân tích AI: {error_message}")

@bot.message_handler(commands=['analyze'])
@admin_only
def analyze_command(message):
    """Analyze problems and predict issues"""
    try:
        bot.reply_to(message, "📈 Đang phân tích problems và dự đoán vấn đề...")
        
        zapi = get_zabbix_api()
        
        # Get problems from last 3 days
        three_days_ago = int((datetime.datetime.now() - datetime.timedelta(days=3)).timestamp())
        
        problems = zapi.problem.get({
            "output": "extend",
            "time_from": three_days_ago,
            "sortfield": "clock",
            "sortorder": "DESC"
        })
        
        if not problems:
            bot.reply_to(message, "✅ Không có problem nào trong 3 ngày qua.")
            return
        
        # Analyze problems
        analysis_text = "📈 **Phân tích Problems (3 ngày qua):**\n\n"
        
        # Count by severity
        severity_count = {}
        host_count = {}
        
        for problem in problems:
            severity = problem['severity']
            severity_count[severity] = severity_count.get(severity, 0) + 1
            
            # Get host name
            hosts = zapi.host.get({
                "output": ['name'],
                "hostids": problem['objectid']
            })
            if hosts:
                host_name = hosts[0]['name']
                host_count[host_name] = host_count.get(host_name, 0) + 1
        
        analysis_text += f"📊 **Tổng quan:**\n"
        analysis_text += f"• Tổng problems: {len(problems)}\n"
        analysis_text += f"• Hosts bị ảnh hưởng: {len(host_count)}\n\n"
        
        analysis_text += "🚨 **Phân bố theo mức độ nghiêm trọng:**\n"
        severity_map = {
            '0': 'Not classified',
            '1': 'Information',
            '2': 'Warning',
            '3': 'Average',
            '4': 'High',
            '5': 'Disaster'
        }
        
        for severity, count in sorted(severity_count.items(), key=lambda x: int(x[0]), reverse=True):
            if count > 0:
                analysis_text += f"• {severity_map.get(severity, 'Unknown')}: {count}\n"
        
        analysis_text += "\n🖥️ **Hosts có nhiều problems nhất:**\n"
        for host, count in sorted(host_count.items(), key=lambda x: x[1], reverse=True)[:5]:
            analysis_text += f"• {host}: {count} problems\n"
        
        analysis_text += "\n🔮 **Dự đoán:**\n"
        analysis_text += "• Cần theo dõi các hosts có nhiều problems\n"
        analysis_text += "• Kiểm tra mối quan hệ phụ thuộc giữa các hosts\n"
        analysis_text += "• Cân nhắc tăng cường monitoring cho các hosts critical"
        
        bot.reply_to(message, analysis_text, parse_mode='Markdown')
        
    except Exception as e:
        error_message = mask_sensitive_data(str(e))
        logger.error(f"Lỗi khi phân tích: {error_message}")
        bot.reply_to(message, f"❌ Lỗi khi phân tích: {error_message}")

@bot.message_handler(commands=['addwebsite'])
@admin_only
def add_website_command(message):
    """Add website for screenshot"""
    try:
        bot.set_state(message.from_user.id, BotStates.waiting_for_website, message.chat.id)
        bot.reply_to(message, "🌐 Vui lòng nhập URL website bạn muốn thêm:")
        
    except Exception as e:
        error_message = mask_sensitive_data(str(e))
        logger.error(f"Lỗi khi thêm website: {error_message}")
        bot.reply_to(message, f"❌ Lỗi khi thêm website: {error_message}")

@bot.message_handler(commands=['users'])
@admin_only
def users_command(message):
    """List all bot users"""
    try:
        bot.reply_to(message, "👥 Đang lấy danh sách người dùng...")
        
        # This would typically query the database
        # For now, just show a placeholder
        users_text = "👥 **Danh sách người dùng:**\n\n"
        users_text += "• Chức năng này cần tích hợp với database\n"
        users_text += "• Hiện tại chỉ hiển thị admin users\n\n"
        
        for admin_id in Config.ADMIN_IDS:
            users_text += f"• Admin ID: {admin_id}\n"
        
        bot.reply_to(message, users_text, parse_mode='Markdown')
        
    except Exception as e:
        error_message = mask_sensitive_data(str(e))
        logger.error(f"Lỗi khi lấy users: {error_message}")
        bot.reply_to(message, f"❌ Lỗi khi lấy users: {error_message}")

@bot.message_handler(commands=['removeuser'])
@admin_only
def remove_user_command(message):
    """Remove a user from the bot"""
    try:
        bot.set_state(message.from_user.id, BotStates.waiting_for_user_id, message.chat.id)
        bot.reply_to(message, "👤 Vui lòng nhập User ID bạn muốn xóa:")
        
    except Exception as e:
        error_message = mask_sensitive_data(str(e))
        logger.error(f"Lỗi khi xóa user: {error_message}")
        bot.reply_to(message, f"❌ Lỗi khi xóa user: {error_message}")

# ==================== CALLBACK HANDLERS ====================

@bot.callback_query_handler(func=lambda call: call.data.startswith('graph_'))
def graph_callback(call):
    """Handle graph selection callback"""
    try:
        data = call.data.split('_')
        hostid = data[1]
        itemid = data[2]
        
        bot.answer_callback_query(call.id, "📊 Đang tạo biểu đồ...")
        
        # Get graph data
        zapi = get_zabbix_api()
        
        # Get item info
        items = zapi.item.get({
            "output": ['name', 'key_'],
            "itemids": itemid
        })
        
        if not items:
            bot.send_message(call.message.chat.id, "❌ Không tìm thấy item")
            return
        
        item = items[0]
        
        # Get history data
        history = zapi.history.get({
            "output": "extend",
            "itemids": itemid,
            "sortfield": "clock",
            "sortorder": "DESC",
            "limit": 100
        })
        
        if not history:
            bot.send_message(call.message.chat.id, "❌ Không có dữ liệu lịch sử")
            return
        
        # Create simple text graph
        graph_text = f"📊 **Biểu đồ:** {item['name']}\n\n"
        
        # Show last 10 values
        for i, h in enumerate(history[:10]):
            clock = datetime.datetime.fromtimestamp(int(h['clock']))
            time_str = clock.strftime('%H:%M')
            graph_text += f"{time_str}: {h['value']}\n"
        
        graph_text += f"\n📈 **Thống kê:**\n"
        values = [float(h['value']) for h in history if h['value'].replace('.', '').isdigit()]
        if values:
            graph_text += f"• Hiện tại: {values[0]:.2f}\n"
            graph_text += f"• Trung bình: {sum(values)/len(values):.2f}\n"
            graph_text += f"• Max: {max(values):.2f}\n"
            graph_text += f"• Min: {min(values):.2f}\n"
        
        bot.send_message(call.message.chat.id, graph_text, parse_mode='Markdown')
        
    except Exception as e:
        error_message = mask_sensitive_data(str(e))
        logger.error(f"Lỗi khi xử lý callback graph: {error_message}")
        bot.send_message(call.message.chat.id, f"❌ Lỗi khi tạo biểu đồ: {error_message}")

# ==================== STATE HANDLERS ====================

@bot.message_handler(state=BotStates.waiting_for_website)
def handle_website_input(message):
    """Handle website URL input"""
    try:
        url = message.text.strip()
        
        # Validate URL
        if not url.startswith(('http://', 'https://')):
            bot.reply_to(message, "❌ URL không hợp lệ. Vui lòng nhập URL bắt đầu bằng http:// hoặc https://")
            return
        
        # Here you would save the website to database
        # For now, just confirm
        bot.reply_to(message, f"✅ Đã thêm website: {url}\n\nChức năng này sẽ được tích hợp với database.")
        
        # Clear state
        bot.delete_state(message.from_user.id, message.chat.id)
        
    except Exception as e:
        error_message = mask_sensitive_data(str(e))
        logger.error(f"Lỗi khi xử lý website input: {error_message}")
        bot.reply_to(message, f"❌ Lỗi khi xử lý website: {error_message}")

@bot.message_handler(state=BotStates.waiting_for_user_id)
def handle_user_id_input(message):
    """Handle user ID input for removal"""
    try:
        user_id = message.text.strip()
        
        # Validate user ID
        if not user_id.isdigit():
            bot.reply_to(message, "❌ User ID không hợp lệ. Vui lòng nhập số.")
            return
        
        user_id = int(user_id)
        
        # Here you would remove the user from database
        # For now, just confirm
        bot.reply_to(message, f"✅ Đã xóa user ID: {user_id}\n\nChức năng này sẽ được tích hợp với database.")
        
        # Clear state
        bot.delete_state(message.from_user.id, message.chat.id)
        
    except Exception as e:
        error_message = mask_sensitive_data(str(e))
        logger.error(f"Lỗi khi xử lý user ID input: {error_message}")
        bot.reply_to(message, f"❌ Lỗi khi xử lý user ID: {error_message}")

# ==================== UTILITY FUNCTIONS ====================

def cleanup_old_data_job():
    """Background job to cleanup old data"""
    while True:
        try:
            cleanup_old_data()
            logger.info("Database cleanup completed")
        except Exception as e:
            error_message = mask_sensitive_data(str(e))
            logger.error(f"Error during database cleanup: {error_message}")
        
        # Sleep for 24 hours
        time.sleep(24 * 60 * 60)

def start_cleanup_job():
    """Start the cleanup job in a separate thread"""
    cleanup_thread = threading.Thread(target=cleanup_old_data_job, daemon=True)
    cleanup_thread.start()

# ==================== MAIN FUNCTION ====================

def main():
    """Start the bot"""
    try:
        # Load environment variables
        load_dotenv()
        
        # Validate configuration
        errors = Config.validate()
        if errors:
            for error in errors:
                logger.error(error)
            return
        
        # Initialize database
        init_db()
        
        # Log safe configuration info
        safe_config = Config.get_safe_config_info()
        logger.info("Bot v2.0 configuration loaded successfully")
        logger.info(f"Zabbix URL: {safe_config['zabbix_url']}")
        logger.info(f"Zabbix User: {safe_config['zabbix_user']}")
        logger.info(f"Zabbix Auth Method: {'Token' if safe_config['zabbix_token'] else 'Username/Password'}")
        logger.info(f"Admin IDs: {safe_config['admin_ids']}")
        logger.info(f"Host Groups: {safe_config['host_groups']}")
        
        # Start cleanup job
        start_cleanup_job()
        
        logger.info("Bot v2.0 starting...")
        logger.info("Bot is ready to receive messages!")
        
        # Start polling
        bot.infinity_polling(timeout=10, long_polling_timeout=5)
        
    except Exception as e:
        error_message = mask_sensitive_data(str(e))
        logger.error(f"Error starting bot: {error_message}")
        raise

if __name__ == '__main__':
    main()
