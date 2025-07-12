import os
import logging
import time
import io
import re
from telegram.ext import ContextTypes
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager
from utils import retry, validate_url
from config import Config

logger = logging.getLogger(__name__)

def extract_url_from_text(text: str) -> str:
    """Extract URL from text using regex"""
    url_pattern = r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+'
    urls = re.findall(url_pattern, text)
    return urls[0] if urls else None

async def take_screenshot(url: str) -> bytes:
    """Take screenshot with retry mechanism and improved error handling"""
    if not validate_url(url):
        logger.error(f"Invalid URL: {url}")
        raise ValueError(f"Invalid URL: {url}")
    
    driver = None
    try:
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument(f"--window-size={Config.SCREENSHOT_WIDTH},{Config.SCREENSHOT_HEIGHT}")
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")

        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
        driver.set_page_load_timeout(30)
        
        logger.info(f"Taking screenshot of: {url}")
        driver.get(url)
        
        # Wait for page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        # Additional wait for dynamic content
        time.sleep(3)
        
        screenshot = driver.get_screenshot_as_png()
        logger.info(f"Screenshot taken successfully for: {url}")
        return screenshot
        
    except TimeoutException:
        logger.error(f"Timeout taking screenshot of: {url}")
        raise
    except WebDriverException as e:
        logger.error(f"WebDriver error taking screenshot of {url}: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error taking screenshot of {url}: {str(e)}")
        raise
    finally:
        if driver:
            try:
                driver.quit()
            except Exception as e:
                logger.error(f"Error closing driver: {str(e)}")

async def send_alert_with_screenshot(chat_id: int, alert_info: dict, context: ContextTypes.DEFAULT_TYPE):
    """Send alert message with optional screenshot"""
    try:
        # Build alert message
        message = f"⚠️ **Cảnh báo mới:**\n"
        message += f"**Host:** {alert_info['host']}\n"
        message += f"**Mô tả:** {alert_info['description']}\n"
        message += f"**Mức độ:** {_get_priority_text(alert_info['priority'])}\n"
        message += f"**Thời gian:** {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(alert_info['timestamp']))}\n"

        await context.bot.send_message(chat_id=chat_id, text=message, parse_mode='Markdown')

        # Try to take screenshot if URL is found
        url = extract_url_from_text(alert_info['description'])
        if url:
            await context.bot.send_message(chat_id=chat_id, text=f"🖼️ Đang chụp ảnh website {url}...")
            try:
                screenshot = await take_screenshot(url)
                await context.bot.send_photo(chat_id=chat_id, photo=io.BytesIO(screenshot))
                await context.bot.send_message(chat_id=chat_id, text="✅ Chụp ảnh thành công!")
            except Exception as screenshot_error:
                logger.error(f"Screenshot failed for {url}: {str(screenshot_error)}")
                await context.bot.send_message(
                    chat_id=chat_id, 
                    text=f"❌ Không thể chụp ảnh website: {str(screenshot_error)}"
                )

    except Exception as e:
        logger.error(f"Error sending alert with screenshot: {str(e)}")
        # Try to send basic message if rich formatting fails
        try:
            basic_message = f"⚠️ Cảnh báo: {alert_info['host']} - {alert_info['description']}"
            await context.bot.send_message(chat_id=chat_id, text=basic_message)
        except Exception as fallback_error:
            logger.error(f"Fallback message also failed: {str(fallback_error)}")

def _get_priority_text(priority: int) -> str:
    """Convert priority number to readable text"""
    priority_map = {
        0: "🔵 Không phân loại",
        1: "🟢 Thông tin", 
        2: "🟡 Cảnh báo",
        3: "🟠 Trung bình",
        4: "🔴 Cao",
        5: "⚫ Thảm họa"
    }
    return priority_map.get(priority, f"Không xác định ({priority})")
