import re
import logging
import time
from typing import Any

logger = logging.getLogger(__name__)

def extract_url_from_text(text: str) -> str:
    """Extract URL from text"""
    url_pattern = r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+'
    urls = re.findall(url_pattern, text)
    return urls[0] if urls else None

def validate_url(url: str) -> bool:
    """Validate URL format"""
    if not isinstance(url, str):
        return False
    # Simple regex to check if it looks like a URL
    return re.match(r'^https?://', url) is not None

def retry(tries=3, delay=5, backoff=2):
    """Retry decorator with exponential backoff"""
    def deco_retry(f):
        def f_retry(*args, **kwargs):
            mtries, mdelay = tries, delay
            while mtries > 1:
                try:
                    return f(*args, **kwargs)
                except Exception as e:
                    msg = f"{str(e)}, Retrying in {mdelay} seconds..."
                    logger.warning(msg)
                    time.sleep(mdelay)
                    mtries -= 1
                    mdelay *= backoff
            return f(*args, **kwargs)
        return f_retry
    return deco_retry

def mask_sensitive_data(text: str) -> str:
    """
    Mask sensitive information in text for logging purposes
    """
    if not text:
        return text
    
    # Mask Zabbix auth token in JSON payload
    text = re.sub(r'("auth":\s*")[^"]+(")', r'\1*****\2', text)
    
    # Mask Telegram Bot Token (format: 123456789:ABCdefGHIjklMNOpqrsTUVwxyz)
    text = re.sub(r'(\d{8,10}):[A-Za-z0-9_-]{35}', r'\1:*****', text)
    # Alternative pattern for Telegram Bot Token
    text = re.sub(r'(\d{8,10}):[A-Za-z0-9_-]+', r'\1:*****', text)
    
    # Mask API keys (common patterns)
    text = re.sub(r'(api[_-]?key["\']?\s*[:=]\s*["\']?)([A-Za-z0-9_-]{20,})(["\']?)', r'\1*****\3', text, flags=re.IGNORECASE)
    
    # Mask passwords (common patterns)
    text = re.sub(r'(password["\']?\s*[:=]\s*["\']?)([^"\']+)(["\']?)', r'\1*****\3', text, flags=re.IGNORECASE)
    text = re.sub(r'(pass["\']?\s*[:=]\s*["\']?)([^"\']+)(["\']?)', r'\1*****\3', text, flags=re.IGNORECASE)
    
    # Mask tokens (common patterns) - improved to catch more cases
    text = re.sub(r'(token["\']?\s*[:=]\s*["\']?)([A-Za-z0-9_-]{20,})(["\']?)', r'\1*****\3', text, flags=re.IGNORECASE)
    
    # Additional patterns for tokens without quotes
    text = re.sub(r'(token:\s*)([A-Za-z0-9_-]{20,})', r'\1*****', text, flags=re.IGNORECASE)
    text = re.sub(r'(token\s+)([A-Za-z0-9_-]{20,})', r'\1*****', text, flags=re.IGNORECASE)
    
    # Mask Zabbix tokens specifically
    text = re.sub(r'(zabbix[_-]?token["\']?\s*[:=]\s*["\']?)([A-Za-z0-9_-]{20,})(["\']?)', r'\1*****\3', text, flags=re.IGNORECASE)
    
    return text

class SensitiveDataFilter(logging.Filter):
    """
    Custom logging filter to mask sensitive data in log messages
    """
    def filter(self, record):
        if hasattr(record, 'msg') and isinstance(record.msg, str):
            record.msg = mask_sensitive_data(record.msg)
        
        if hasattr(record, 'args') and record.args:
            if isinstance(record.args, tuple):
                record.args = tuple(mask_sensitive_data(str(arg)) if isinstance(arg, str) else arg 
                                  for arg in record.args)
            elif isinstance(record.args, dict):
                record.args = {k: mask_sensitive_data(str(v)) if isinstance(v, str) else v 
                              for k, v in record.args.items()}
        
        return True

def setup_secure_logging():
    """
    Setup logging with sensitive data masking
    """
    # Get the root logger
    root_logger = logging.getLogger()
    
    # Add the sensitive data filter to all handlers
    for handler in root_logger.handlers:
        handler.addFilter(SensitiveDataFilter())
    
    # Also add to the root logger itself
    root_logger.addFilter(SensitiveDataFilter())

def log_safe(message: str, *args, **kwargs):
    """
    Safe logging function that automatically masks sensitive data
    """
    safe_message = mask_sensitive_data(message)
    logger = logging.getLogger(__name__)
    logger.info(safe_message, *args, **kwargs)
