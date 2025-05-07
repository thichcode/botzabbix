import os
import logging
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from zabbix_api import ZabbixAPI
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import time
import io
import sqlite3
import re
import requests
import datetime
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Initialize Zabbix API
zapi = ZabbixAPI(os.getenv('ZABBIX_URL'))
zapi.login(os.getenv('ZABBIX_USER'), os.getenv('ZABBIX_PASSWORD'))

# List of admin IDs allowed to use the bot
ADMIN_IDS = [int(id) for id in os.getenv('ADMIN_IDS', '').split(',') if id]

# Data retention period in seconds (3 months)
DATA_RETENTION_PERIOD = 90 * 24 * 60 * 60

def cleanup_old_data():
    """Clean up data older than retention period"""
    try:
        conn = sqlite3.connect('zabbix_alerts.db')
        c = conn.cursor()
        
        # Calculate cutoff timestamp
        cutoff_time = int(time.time()) - DATA_RETENTION_PERIOD
        
        # Delete old alerts
        c.execute('DELETE FROM alerts WHERE timestamp < ?', (cutoff_time,))
        
        # Delete old error patterns that haven't been updated
        c.execute('DELETE FROM error_patterns WHERE last_updated < ?', (cutoff_time,))
        
        # Log cleanup results
        alerts_deleted = c.rowcount
        logger.info(f"Cleaned up {alerts_deleted} old records")
        
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Error cleaning up old data: {str(e)}")

def init_db():
    """Initialize SQLite database"""
    conn = sqlite3.connect('zabbix_alerts.db')
    c = conn.cursor()
    
    # Alerts table
    c.execute('''CREATE TABLE IF NOT EXISTS alerts
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  trigger_id TEXT,
                  host TEXT,
                  description TEXT,
                  priority INTEGER,
                  timestamp INTEGER,
                  status TEXT,
                  resolution TEXT,
                  analysis TEXT)''')
    
    # Error patterns table with last_updated field
    c.execute('''CREATE TABLE IF NOT EXISTS error_patterns
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  pattern TEXT,
                  description TEXT,
                  solution TEXT,
                  frequency INTEGER,
                  last_updated INTEGER)''')
    
    # Users table
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY,
                  username TEXT,
                  first_name TEXT,
                  last_name TEXT,
                  join_date INTEGER,
                  is_active BOOLEAN DEFAULT 1)''')
    
    conn.commit()
    conn.close()
    
    # Run initial cleanup
    cleanup_old_data()

def save_user(user_id: int, username: str, first_name: str, last_name: str):
    """Save user information to database"""
    try:
        conn = sqlite3.connect('zabbix_alerts.db')
        c = conn.cursor()
        
        c.execute('''INSERT OR REPLACE INTO users 
                     (id, username, first_name, last_name, join_date, is_active)
                     VALUES (?, ?, ?, ?, ?, 1)''',
                  (user_id, username, first_name, last_name, int(time.time())))
        
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Error saving user info: {str(e)}")

def remove_user(user_id: int):
    """Remove user from database"""
    try:
        conn = sqlite3.connect('zabbix_alerts.db')
        c = conn.cursor()
        
        c.execute('UPDATE users SET is_active = 0 WHERE id = ?', (user_id,))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Error removing user: {str(e)}")
        return False

def extract_url_from_text(text: str) -> str:
    """Extract URL from text"""
    url_pattern = r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+'
    urls = re.findall(url_pattern, text)
    return urls[0] if urls else None

async def take_screenshot(url: str) -> bytes:
    """Chụp ảnh màn hình website và trả về dạng bytes"""
    try:
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument(f"--window-size={os.getenv('SCREENSHOT_WIDTH', '1920')},{os.getenv('SCREENSHOT_HEIGHT', '1080')}")

        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
        driver.get(url)
        time.sleep(2)  # Đợi trang load

        screenshot = driver.get_screenshot_as_png()
        driver.quit()
        return screenshot
    except Exception as e:
        logger.error(f"Lỗi khi chụp ảnh: {str(e)}")
        return None

async def add_host_website(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Thêm URL website cho host"""
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("Bạn không có quyền sử dụng lệnh này.")
        return

    if len(context.args) < 2:
        await update.message.reply_text("Vui lòng cung cấp host và URL website.\nVí dụ: /addwebsite host1 https://example.com")
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
        
        await update.message.reply_text(f"Đã thêm website {url} cho host {host}")
    except Exception as e:
        await update.message.reply_text(f"Lỗi khi thêm website: {str(e)}")

async def get_host_website(host: str) -> tuple:
    """Lấy thông tin website của host"""
    try:
        conn = sqlite3.connect('zabbix_alerts.db')
        c = conn.cursor()
        
        c.execute('SELECT website_url, screenshot_enabled FROM host_websites WHERE host = ?', (host,))
        result = c.fetchone()
        
        conn.close()
        return result if result else (None, False)
    except Exception as e:
        logger.error(f"Lỗi khi lấy thông tin website: {str(e)}")
        return None, False

async def send_alert_with_screenshot(chat_id: int, alert_info: dict, context: ContextTypes.DEFAULT_TYPE):
    """Gửi cảnh báo kèm ảnh chụp màn hình nếu có URL trong trigger"""
    try:
        # Tạo message cảnh báo
        message = f"⚠️ Cảnh báo mới:\n"
        message += f"Host: {alert_info['host']}\n"
        message += f"Mô tả: {alert_info['description']}\n"
        message += f"Mức độ: {alert_info['priority']}\n"
        message += f"Thời gian: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(alert_info['timestamp']))}\n"

        # Gửi message cảnh báo
        await context.bot.send_message(chat_id=chat_id, text=message)

        # Kiểm tra và trích xuất URL từ mô tả cảnh báo
        url = extract_url_from_text(alert_info['description'])
        if url:
            await context.bot.send_message(chat_id=chat_id, text=f"Đang chụp ảnh website {url}...")
            screenshot = await take_screenshot(url)
            if screenshot:
                await context.bot.send_photo(chat_id=chat_id, photo=io.BytesIO(screenshot))
            else:
                await context.bot.send_message(chat_id=chat_id, text="Không thể chụp ảnh website")

    except Exception as e:
        logger.error(f"Lỗi khi gửi cảnh báo: {str(e)}")

async def get_alerts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get latest alerts"""
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("You don't have permission to use this command.")
        return

    try:
        alerts = zapi.trigger.get({
            "output": ["description", "lastchange", "priority", "triggerid"],
            "selectHosts": ["host"],
            "sortfield": "lastchange",
            "sortorder": "DESC",
            "limit": 10
        })

        for alert in alerts:
            host = alert['hosts'][0]['host'] if alert['hosts'] else "Unknown"
            alert_info = {
                'trigger_id': alert['triggerid'],
                'host': host,
                'description': alert['description'],
                'priority': alert['priority'],
                'timestamp': int(alert['lastchange'])
            }
            
            # Save alert to database
            save_alert(
                alert_info['trigger_id'],
                alert_info['host'],
                alert_info['description'],
                alert_info['priority'],
                alert_info['timestamp']
            )
            
            # Send alert with screenshot if URL exists
            await send_alert_with_screenshot(update.effective_chat.id, alert_info, context)

    except Exception as e:
        await update.message.reply_text(f"Error getting alerts: {str(e)}")

async def get_hosts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get list of monitored hosts"""
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("You don't have permission to use this command.")
        return

    try:
        hosts = zapi.host.get({
            "output": ["host", "status"],
            "selectInterfaces": ["ip"]
        })

        message = "List of hosts:\n\n"
        for host in hosts:
            status = "Online" if host['status'] == '0' else "Offline"
            ip = host['interfaces'][0]['ip'] if host['interfaces'] else "N/A"
            message += f"- {host['host']}\n"
            message += f"  IP: {ip}\n"
            message += f"  Status: {status}\n\n"

        await update.message.reply_text(message)
    except Exception as e:
        await update.message.reply_text(f"Error getting host list: {str(e)}")

async def get_graph(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get performance graph for an item"""
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
        # Find host ID
        hosts = zapi.host.get({
            "filter": {"host": host},
            "output": ["hostid"]
        })
        
        if not hosts:
            await update.message.reply_text(f"Host {host} not found")
            return

        hostid = hosts[0]["hostid"]

        # Find item ID
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

        # Get history data
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

        # Create graph
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

        # Save graph to buffer
        buf = io.BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight')
        buf.seek(0)
        plt.close()

        # Send graph
        await update.message.reply_photo(photo=buf)
        
    except Exception as e:
        await update.message.reply_text(f"Error creating graph: {str(e)}")

async def take_zabbix_dashboard_screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Take screenshot of Zabbix dashboard"""
    try:
        await update.message.reply_text("Taking screenshot of Zabbix dashboard...")
        
        # Configure Chrome
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument(f"--window-size={os.getenv('SCREENSHOT_WIDTH', '1920')},{os.getenv('SCREENSHOT_HEIGHT', '1080')}")

        # Initialize driver
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
        
        try:
            # Login to Zabbix
            zabbix_url = os.getenv('ZABBIX_URL')
            driver.get(zabbix_url)
            
            # Wait for login form
            time.sleep(2)
            
            # Fill login information
            username_field = driver.find_element("name", "name")
            password_field = driver.find_element("name", "password")
            
            username_field.send_keys(os.getenv('ZABBIX_USER'))
            password_field.send_keys(os.getenv('ZABBIX_PASSWORD'))
            
            # Click login button
            login_button = driver.find_element("xpath", "//button[@type='submit']")
            login_button.click()
            
            # Wait for login success
            time.sleep(5)
            
            # Take screenshot
            screenshot = driver.get_screenshot_as_png()
            
            # Send image
            await update.message.reply_photo(photo=io.BytesIO(screenshot))
            
        finally:
            driver.quit()
            
    except Exception as e:
        await update.message.reply_text(f"Error taking dashboard screenshot: {str(e)}")

async def ask_ai(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send question to AI (Open WebUI) and get response about Zabbix data"""
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("Bạn không có quyền sử dụng lệnh này.")
        return

    if not context.args:
        await update.message.reply_text("Vui lòng nhập câu hỏi về dữ liệu Zabbix.")
        return

    try:
        # Lấy dữ liệu Zabbix
        end_time = int(time.time())
        start_time = end_time - 86400 * 7  # 7 ngày gần nhất

        # Lấy thông tin alerts
        alerts = zapi.trigger.get({
            "output": ["description", "lastchange", "priority"],
            "sortfield": "lastchange",
            "sortorder": "DESC",
            "time_from": start_time,
            "time_till": end_time
        })

        # Lấy thông tin hosts
        hosts = zapi.host.get({
            "output": ["host", "status"],
            "selectInterfaces": ["ip"]
        })

        # Chuẩn bị dữ liệu cho AI
        zabbix_data = {
            "alerts": alerts,
            "hosts": hosts,
            "time_range": {
                "start": start_time,
                "end": end_time
            }
        }

        # Tạo prompt cho AI
        prompt = f"""Dữ liệu Zabbix trong 7 ngày qua:
- Số lượng cảnh báo: {len(alerts)}
- Số lượng host: {len(hosts)}
- Thời gian: từ {time.strftime('%Y-%m-%d', time.localtime(start_time))} đến {time.strftime('%Y-%m-%d', time.localtime(end_time))}

Câu hỏi: {' '.join(context.args)}

Hãy phân tích dữ liệu và trả lời câu hỏi trên."""

        # Gọi API Open WebUI
        api_url = os.getenv('OPENWEBUI_API_URL')
        api_key = os.getenv('OPENWEBUI_API_KEY')

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
        await update.message.reply_text(f"Lỗi khi phân tích dữ liệu: {str(e)}")

async def analyze_and_predict(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Analyze and predict trends"""
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("You don't have permission to use this command.")
        return

    try:
        # Get alert history
        end_time = int(time.time())
        start_time = end_time - 86400 * 7  # 7 days

        triggers = zapi.trigger.get({
            "output": ["description", "lastchange", "priority"],
            "sortfield": "lastchange",
            "sortorder": "DESC",
            "time_from": start_time,
            "time_till": end_time
        })

        # Analyze patterns
        patterns = {}
        for trigger in triggers:
            desc = trigger['description']
            if desc in patterns:
                patterns[desc] += 1
            else:
                patterns[desc] = 1

        # Create analysis report
        report = "📊 Analysis and Predictions:\n\n"
        
        # Alert statistics
        report += "1. Alert Statistics:\n"
        for desc, count in sorted(patterns.items(), key=lambda x: x[1], reverse=True):
            report += f"- {desc}: {count} times\n"

        # Trend predictions
        report += "\n2. Trend Predictions:\n"
        for desc, count in sorted(patterns.items(), key=lambda x: x[1], reverse=True)[:3]:
            if count > 5:
                report += f"- {desc} is likely to occur again\n"

        # Send report
        await update.message.reply_text(report)

    except Exception as e:
        await update.message.reply_text(f"Error during analysis: {str(e)}")

def save_alert(trigger_id: str, host: str, description: str, priority: int, timestamp: int):
    """Save alert to database"""
    try:
        conn = sqlite3.connect('zabbix_alerts.db')
        c = conn.cursor()
        
        # Check if alert already exists
        c.execute('SELECT id FROM alerts WHERE trigger_id = ? AND timestamp = ?', 
                 (trigger_id, timestamp))
        if c.fetchone():
            return
        
        c.execute('''INSERT INTO alerts 
                     (trigger_id, host, description, priority, timestamp)
                     VALUES (?, ?, ?, ?, ?)''',
                  (trigger_id, host, description, priority, timestamp))
        
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Error saving alert: {str(e)}")

def update_error_pattern(pattern: str, description: str, solution: str):
    """Update error pattern in database"""
    try:
        conn = sqlite3.connect('zabbix_alerts.db')
        c = conn.cursor()
        
        current_time = int(time.time())
        
        c.execute('''INSERT OR REPLACE INTO error_patterns 
                     (pattern, description, solution, frequency, last_updated)
                     VALUES (?, ?, ?, 
                            COALESCE((SELECT frequency + 1 FROM error_patterns WHERE pattern = ?), 1),
                            ?)''',
                  (pattern, description, solution, pattern, current_time))
        
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Error updating error pattern: {str(e)}")

async def remove_user_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Remove user from bot"""
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("You don't have permission to use this command.")
        return

    if not context.args:
        await update.message.reply_text("Please provide user ID to remove.")
        return

    try:
        user_id = int(context.args[0])
        if remove_user(user_id):
            await update.message.reply_text(f"User with ID {user_id} has been removed from bot.")
        else:
            await update.message.reply_text(f"Could not remove user with ID {user_id}.")
    except ValueError:
        await update.message.reply_text("Invalid user ID.")

async def list_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List all users"""
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("You don't have permission to use this command.")
        return

    try:
        conn = sqlite3.connect('zabbix_alerts.db')
        c = conn.cursor()
        
        c.execute('SELECT id, username, first_name, last_name, join_date, is_active FROM users')
        users = c.fetchall()
        
        conn.close()

        if not users:
            await update.message.reply_text("No users in database.")
            return

        message = "📋 User List:\n\n"
        for user in users:
            user_id, username, first_name, last_name, join_date, is_active = user
            status = "✅ Active" if is_active else "❌ Removed"
            join_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(join_date))
            message += f"ID: {user_id}\n"
            message += f"Username: @{username if username else 'N/A'}\n"
            message += f"Name: {first_name} {last_name if last_name else ''}\n"
            message += f"Join Date: {join_time}\n"
            message += f"Status: {status}\n\n"

        await update.message.reply_text(message)
    except Exception as e:
        await update.message.reply_text(f"Error getting user list: {str(e)}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    user = update.effective_user
    user_id = user.id
    
    # Save user information
    save_user(user_id, user.username, user.first_name, user.last_name)
    
    # Check admin privileges
    if user_id not in ADMIN_IDS:
        await update.message.reply_text(
            f"Hello {user.first_name}!\n"
            f"Your ID is: {user_id}\n"
            "You don't have permission to use this bot.\n"
            "Please contact admin for access."
        )
        return
    
    await update.message.reply_text(
        f"Welcome to Zabbix Bot!\n"
        f"Your ID is: {user_id}\n\n"
        "Available commands:\n"
        "/dashboard - Take screenshot of Zabbix dashboard\n"
        "/alerts - View latest alerts (admin only)\n"
        "/hosts - List monitored hosts (admin only)\n"
        "/problems - View active problems (admin only)\n"
        "/users - List all users (admin only)\n"
        "/removeuser - Remove a user (admin only)"
    )

async def get_active_problems(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get last 20 active problems from Zabbix dashboard ID 10 with severity >= Warning"""
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("Bạn không có quyền sử dụng lệnh này.")
        return

    try:
        # Get dashboard items for dashboard ID 10
        dashboard_items = zapi.dashboard.get({
            "output": ["dashboardid"],
            "filter": {"dashboardid": "10"},
            "selectPages": ["dashboard_pageid"],
            "selectWidgets": ["widgetid", "type", "name"]
        })

        if not dashboard_items:
            await update.message.reply_text("Không tìm thấy dashboard ID 10.")
            return

        # Get all hosts from dashboard widgets
        dashboard_hosts = set()
        for item in dashboard_items:
            for page in item.get('pages', []):
                for widget in page.get('widgets', []):
                    if widget.get('type') in ['problems', 'problemhosts']:
                        # Get hosts from widget
                        widget_hosts = zapi.host.get({
                            "output": ["hostid"],
                            "filter": {"host": widget.get('name', '')}
                        })
                        for host in widget_hosts:
                            dashboard_hosts.add(host['hostid'])

        # Get active problems for these hosts with severity >= Warning (2)
        problems = zapi.problem.get({
            "output": ["eventid", "name", "severity", "clock"],
            "selectTags": ["tag", "value"],
            "selectHosts": ["host"],
            "hostids": list(dashboard_hosts),
            "severities": ["2", "3", "4", "5"],  # Warning, Average, High, Disaster
            "sortfield": "clock",
            "sortorder": "DESC",
            "limit": 20
        })

        if not problems:
            await update.message.reply_text("Không có problem nào đang tồn tại trong dashboard.")
            return

        message = "🔴 Danh sách 20 problem đang tồn tại trong dashboard (từ Warning trở lên):\n\n"
        for problem in problems:
            # Get host name
            host = problem['hosts'][0]['host'] if problem['hosts'] else "Unknown"
            
            # Format severity with emoji
            severity_map = {
                "2": "⚠️ Warning",
                "3": "⚠️ Average",
                "4": "🚨 High",
                "5": "💥 Disaster"
            }
            severity = severity_map.get(problem['severity'], "Unknown")
            
            # Format time
            time_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(int(problem['clock'])))
            
            # Format tags
            tags = [f"{tag['tag']}: {tag['value']}" for tag in problem['tags']] if 'tags' in problem else []
            tags_str = "\n  Tags: " + ", ".join(tags) if tags else ""
            
            message += f"Host: {host}\n"
            message += f"Problem: {problem['name']}\n"
            message += f"Mức độ: {severity}\n"
            message += f"Thời gian: {time_str}{tags_str}\n\n"

        await update.message.reply_text(message)

    except Exception as e:
        await update.message.reply_text(f"Lỗi khi lấy danh sách problem: {str(e)}")

def main():
    """Start the bot"""
    # Initialize database
    init_db()
    
    application = Application.builder().token(os.getenv('TELEGRAM_BOT_TOKEN')).build()

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("alerts", get_alerts))
    application.add_handler(CommandHandler("hosts", get_hosts))
    application.add_handler(CommandHandler("problems", get_active_problems))
    application.add_handler(CommandHandler("graph", get_graph))
    application.add_handler(CommandHandler("dashboard", take_zabbix_dashboard_screenshot))
    application.add_handler(CommandHandler("askai", ask_ai))
    application.add_handler(CommandHandler("analyze", analyze_and_predict))
    application.add_handler(CommandHandler("removeuser", remove_user_command))
    application.add_handler(CommandHandler("users", list_users))

    # Schedule periodic cleanup
    application.job_queue.run_repeating(
        lambda context: cleanup_old_data(),
        interval=24 * 60 * 60,  # Run daily
        first=10  # Start after 10 seconds
    )

    # Run bot
    application.run_polling()

if __name__ == '__main__':
    main() 