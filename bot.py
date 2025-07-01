import os
import logging
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
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
from contextlib import contextmanager
from typing import Optional, Dict, Any

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

DB_PATH = 'zabbix_alerts.db'
DB_TIMEOUT = 10  # Assuming a default timeout

def get_zabbix_api():
    from zabbix_api import ZabbixAPI

    # Ensure ZABBIX_URL is set
    zabbix_url = os.getenv('ZABBIX_URL')
    if not zabbix_url:
        raise ValueError("Environment variable 'ZABBIX_URL' is not set.")

    zapi = ZabbixAPI(zabbix_url)
    zapi.login(os.getenv('ZABBIX_USER'), os.getenv('ZABBIX_PASSWORD'))
    return zapi

# List of admin IDs allowed to use the bot
ADMIN_IDS = [int(id) for id in os.getenv('ADMIN_IDS', '').split(',') if id]

# Data retention period in seconds (3 months)
DATA_RETENTION_PERIOD = 90 * 24 * 60 * 60

@contextmanager
def get_db_connection(db_path=DB_PATH):
    """Context manager for database connections"""
    conn = None
    try:
        conn = sqlite3.connect(db_path, timeout=DB_TIMEOUT)
        conn.row_factory = sqlite3.Row
        yield conn
    except sqlite3.Error as e:
        logger.error(f"Database error: {e}")
        raise DatabaseError(f"Database connection error: {str(e)}")
    finally:
        if conn:
            try:
                conn.close()
            except Exception as e:
                logger.error(f"Error closing database connection: {e}")

def init_db(db_path=DB_PATH):
    """Initialize SQLite database with indexes"""
    try:
        with get_db_connection(db_path) as conn:
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
            
            # Host websites table
            c.execute('''CREATE TABLE IF NOT EXISTS host_websites
                         (host TEXT PRIMARY KEY,
                          website_url TEXT,
                          screenshot_enabled BOOLEAN DEFAULT 1)''')
            
            conn.commit()
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        raise

def save_user(user_id: int, username: str, first_name: str, last_name: str, db_path=DB_PATH) -> bool:
    """Save user information to database with error handling"""
    try:
        with get_db_connection(db_path) as conn:
            c = conn.cursor()
            c.execute('''INSERT OR REPLACE INTO users 
                         (id, username, first_name, last_name, join_date, is_active)
                         VALUES (?, ?, ?, ?, ?, 1)''',
                      (user_id, username, first_name, last_name, int(time.time())))
            conn.commit()
        return True
    except Exception as e:
        logger.error(f"Error saving user: {e}")
        return False

def get_user(user_id: int, db_path=DB_PATH) -> Optional[Dict[str, Any]]:
    """Get user information from database"""
    try:
        with get_db_connection(db_path) as conn:
            c = conn.cursor()
            c.execute('SELECT * FROM users WHERE id = ?', (user_id,))
            row = c.fetchone()
            return dict(row) if row else None
    except Exception as e:
        logger.error(f"Error getting user: {e}")
        return None

def remove_user(user_id: int, db_path=DB_PATH):
    """Remove user from database"""
    try:
        with get_db_connection(db_path) as conn:
            c = conn.cursor()
            c.execute('UPDATE users SET is_active = 0 WHERE id = ?', (user_id,))
            conn.commit()
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

        try:
            driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
        except Exception as e:
            logger.error(f"Error in Chrome driver setup: {str(e)}")
            return None

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
        logger.error(f"Error inserting host website: {str(e)}")
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
        logger.error(f"Error fetching host website: {str(e)}")
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
        logger.error(f"Error sending alert with screenshot: {str(e)}")

async def get_alerts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get latest alerts"""
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("You don't have permission to use this command.")
        return

    try:
        zapi = get_zabbix_api()
        alerts = zapi.trigger.get({
            "output": ["description", "lastchange", "priority", "triggerid"],
            "selectHosts": ["host"],
            "sortfield": "lastchange",
            "sortorder": "DESC",
            "limit": 10
        })
    except Exception as e:
        logger.error(f"Error fetching latest alerts: {str(e)}")
        await update.message.reply_text(f"Error fetching latest alerts: {str(e)}")
        return

    try:
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
        logger.error(f"Error processing alerts: {str(e)}")
        await update.message.reply_text(f"Error getting alerts: {str(e)}")

async def get_hosts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get list of monitored hosts"""
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("You don't have permission to use this command.")
        return

    try:
        zapi = get_zabbix_api()
        hosts = zapi.host.get({
            "output": ["host", "status"],
            "selectInterfaces": ["ip"]
        })
    except Exception as e:
        logger.error(f"Error fetching monitored hosts: {str(e)}")
        await update.message.reply_text(f"Error fetching monitored hosts: {str(e)}")
        return

    try:
        message = "List of hosts:\n\n"
        for host in hosts:
            status = "Online" if host['status'] == '0' else "Offline"
            ip = host['interfaces'][0]['ip'] if host['interfaces'] else "N/A"
            message += f"- {host['host']}\n"
            message += f"  IP: {ip}\n"
            message += f"  Status: {status}\n\n"

        await update.message.reply_text(message)
    except Exception as e:
        logger.error(f"Error processing host list: {str(e)}")
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
        zapi = get_zabbix_api()
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
        logger.error(f"Error creating graph: {str(e)}")
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
        logger.error(f"Error taking dashboard screenshot: {str(e)}")
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
        zapi = get_zabbix_api()
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
        logger.error(f"Error in AI analysis: {str(e)}")
        await update.message.reply_text(f"Lỗi khi phân tích dữ liệu: {str(e)}")

async def analyze_and_predict(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Analyze historical alerts and predict potential future issues based on patterns."""
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("You don't have permission to use this command.")
        return

    try:
        await update.message.reply_text("Đang phân tích và dự đoán xu hướng cảnh báo...")
        zapi = get_zabbix_api()
        # Get alert history for the last 7 days
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
            await update.message.reply_text("Không có dữ liệu cảnh báo nào trong 7 ngày qua để phân tích.")
            return

        # Analyze patterns by description and host
        patterns = {}
        host_alerts = {}
        daily_counts = {}
        for trigger in triggers:
            desc = trigger['description']
            host = trigger['hosts'][0]['host'] if trigger['hosts'] else "Unknown"
            timestamp = int(trigger['lastchange'])
            day = time.strftime('%Y-%m-%d', time.localtime(timestamp))
            
            # Count by description
            if desc in patterns:
                patterns[desc] += 1
            else:
                patterns[desc] = 1
                
            # Count by host
            if host in host_alerts:
                host_alerts[host] += 1
            else:
                host_alerts[host] = 1
                
            # Count by day for trend analysis
            if day in daily_counts:
                daily_counts[day] += 1
            else:
                daily_counts[day] = 1

        # Create analysis report
        report = "📊 Báo cáo phân tích và dự đoán xu hướng (7 ngày qua):\n\n"
        report += f"Tổng số cảnh báo: {len(triggers)}\n\n"
        
        # Most frequent alerts
        report += "🔥 Các cảnh báo thường xuyên nhất:\n"
        sorted_patterns = sorted(patterns.items(), key=lambda x: x[1], reverse=True)[:5]
        for desc, count in sorted_patterns:
            report += f"- {desc}: {count} lần\n"
        report += "\n"
        
        # Hosts with most alerts
        report += "🖥️ Các host có nhiều cảnh báo nhất:\n"
        sorted_hosts = sorted(host_alerts.items(), key=lambda x: x[1], reverse=True)[:5]
        for host, count in sorted_hosts:
            report += f"- {host}: {count} cảnh báo\n"
        report += "\n"
        
        # Daily trend
        report += "📅 Xu hướng cảnh báo theo ngày:\n"
        sorted_days = sorted(daily_counts.items(), key=lambda x: x[0])
        for day, count in sorted_days:
            report += f"- {day}: {count} cảnh báo\n"
        report += "\n"
        
        # Simple prediction based on frequency
        report += "🔮 Dự đoán:\n"
        if sorted_patterns:
            most_frequent = sorted_patterns[0]
            report += f"- Cảnh báo '{most_frequent[0]}' có khả năng xảy ra tiếp theo do tần suất cao ({most_frequent[1]} lần).\n"
        if sorted_hosts:
            most_affected = sorted_hosts[0]
            report += f"- Host '{most_affected[0]}' có khả năng gặp vấn đề tiếp theo ({most_affected[1]} cảnh báo).\n"
        
        await update.message.reply_text(report)
        
    except Exception as e:
        logger.error(f"Error in analyze_and_predict: {str(e)}")
        await update.message.reply_text(f"Lỗi khi phân tích và dự đoán xu hướng: {str(e)}")

def save_alert(trigger_id, host, description, priority, timestamp, db_path=DB_PATH):
    """Save alert to database"""
    try:
        with get_db_connection(db_path) as conn:
            c = conn.cursor()
            c.execute('''INSERT INTO alerts 
                         (trigger_id, host, description, priority, timestamp)
                         VALUES (?, ?, ?, ?, ?)''',
                      (trigger_id, host, description, priority, timestamp))
            conn.commit()
            return True
    except Exception as e:
        logger.error(f"Error saving alert: {e}")
        return False

def add_error_pattern(pattern: str, db_path=DB_PATH) -> bool:
    """Thêm error pattern vào database"""
    try:
        with get_db_connection(db_path) as conn:
            c = conn.cursor()
            c.execute('''INSERT OR REPLACE INTO error_patterns 
                         (pattern, description, solution, frequency, last_updated)
                         VALUES (?, NULL, NULL, 0, ?)''',
                      (pattern, int(time.time())))
            conn.commit()
        return True
    except Exception as e:
        logger.error(f"Error adding error pattern: {e}")
        return False

def get_error_patterns(db_path=DB_PATH) -> list:
    """Lấy danh sách error patterns từ database"""
    try:
        with get_db_connection(db_path) as conn:
            c = conn.cursor()
            c.execute('SELECT pattern FROM error_patterns')
            return [row['pattern'] for row in c.fetchall()]
    except Exception as e:
        logger.error(f"Error getting error patterns: {e}")
        return []

def remove_error_pattern(pattern: str, db_path=DB_PATH) -> bool:
    """Xóa error pattern khỏi database"""
    try:
        with get_db_connection(db_path) as conn:
            c = conn.cursor()
            c.execute('DELETE FROM error_patterns WHERE pattern = ?', (pattern,))
            conn.commit()
        return True
    except Exception as e:
        logger.error(f"Error removing error pattern: {e}")
        return False

def cleanup_old_data(db_path=DB_PATH, retention_period=DATA_RETENTION_PERIOD):
    """Xóa dữ liệu cũ khỏi database"""
    try:
        cutoff_time = int(time.time()) - retention_period
        with get_db_connection(db_path) as conn:
            c = conn.cursor()
            # Xóa alerts cũ
            c.execute('DELETE FROM alerts WHERE timestamp < ?', (cutoff_time,))
            alerts_deleted = c.rowcount
            # Xóa error patterns cũ
            c.execute('DELETE FROM error_patterns WHERE last_updated < ?', (cutoff_time,))
            patterns_deleted = c.rowcount
            conn.commit()
            logger.info(f"Cleaned up {alerts_deleted} old alerts and {patterns_deleted} old patterns")
    except Exception as e:
        logger.error(f"Error cleaning up old data: {e}")

async def process_alerts_batch(alerts: list, context: ContextTypes.DEFAULT_TYPE):
    """Xử lý một batch alerts"""
    try:
        for alert in alerts:
            # Lưu alert vào database
            save_alert(
                alert['triggerid'],
                alert['hosts'][0]['host'],
                alert['description'],
                alert['priority'],
                int(alert['lastchange'])
            )
            
            # Gửi alert cho tất cả users
            with get_db_connection() as conn:
                c = conn.cursor()
                c.execute('SELECT id FROM users WHERE is_active = 1')
                users = c.fetchall()
                
                for user in users:
                    await send_alert_with_screenshot(user['id'], {
                        'host': alert['hosts'][0]['host'],
                        'description': alert['description'],
                        'priority': alert['priority'],
                        'timestamp': int(alert['lastchange'])
                    }, context)
    except Exception as e:
        logger.error(f"Error processing alerts batch: {e}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a welcome message when the command /start is issued."""
    user = update.effective_user
    if user.id not in ADMIN_IDS:
        await update.message.reply_text("Bạn không có quyền sử dụng bot này.")
        return
    save_user(user.id, user.username, user.first_name, user.last_name)
    await update.message.reply_text(
        f"Chào {user.first_name}!\n"
        "Tôi là bot theo dõi cảnh báo Zabbix.\n"
        "Các lệnh khả dụng:\n"
        "/getalerts - Lấy các cảnh báo mới nhất\n"
        "/gethosts - Lấy danh sách host\n"
        "/graph <host> <item_key> [period] - Lấy biểu đồ hiệu suất\n"
        "/dashboard - Chụp ảnh dashboard Zabbix\n"
        "/ask <câu hỏi> - Hỏi AI về dữ liệu Zabbix\n"
        "/analyze - Phân tích và dự đoán xu hướng\n"
        "/addwebsite <host> <url> [enabled] - Thêm website cho host"
    )

def main() -> None:
    """Start the bot."""
    # Initialize database
    init_db()
    
    # Create the Application and pass it your bot's token.
    application = Application.builder().token(os.getenv('TELEGRAM_BOT_TOKEN')).build()

    # Add handlers for commands
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("getalerts", get_alerts))
    application.add_handler(CommandHandler("gethosts", get_hosts))
    application.add_handler(CommandHandler("graph", get_graph))
    application.add_handler(CommandHandler("dashboard", take_zabbix_dashboard_screenshot))
    application.add_handler(CommandHandler("ask", ask_ai))
    application.add_handler(CommandHandler("analyze", analyze_and_predict))
    application.add_handler(CommandHandler("addwebsite", add_host_website))

    # Start the Bot
    logger.info("Starting bot...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
