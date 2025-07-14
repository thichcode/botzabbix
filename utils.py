import re
import logging

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
