import os
import logging
import time
import io
from telegram import Update
from telegram.ext import ContextTypes
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from config import Config
from decorators import admin_only

logger = logging.getLogger(__name__)

class DashboardCommand:
    @admin_only
    async def execute(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            await update.message.reply_text("Đang chụp ảnh dashboard Zabbix...")
            
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument(f"--window-size={Config.SCREENSHOT_WIDTH},{Config.SCREENSHOT_HEIGHT}")

            driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
            
            try:
                zabbix_url = Config.ZABBIX_URL
                driver.get(zabbix_url)
                
                time.sleep(2)
                
                username_field = driver.find_element("name", "name")
                password_field = driver.find_element("name", "password")
                
                username_field.send_keys(Config.ZABBIX_USER)
                password_field.send_keys(Config.ZABBIX_PASSWORD)
                
                login_button = driver.find_element("xpath", "//button[@type='submit']")
                login_button.click()
                
                time.sleep(5)
                
                screenshot = driver.get_screenshot_as_png()
                
                await update.message.reply_photo(photo=io.BytesIO(screenshot))
                
            finally:
                driver.quit()
                
        except Exception as e:
            logger.error(f"Lỗi khi chụp ảnh dashboard: {str(e)}")
            await update.message.reply_text(f"Lỗi khi chụp ảnh dashboard: {str(e)}")
