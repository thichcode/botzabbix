import os
import logging
import time
import io
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

@retry(tries=3, delay=5, backoff=2)
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
