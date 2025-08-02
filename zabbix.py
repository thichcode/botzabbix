import os
import logging
from zabbix_api import ZabbixAPI
from config import Config

logger = logging.getLogger(__name__)

def get_zabbix_api():
    if not Config.ZABBIX_URL:
        raise ValueError("ZABBIX_URL is not configured.")

    session_kwargs = {}
    if Config.USE_PROXY:
        http_proxy = os.getenv('HTTP_PROXY')
        https_proxy = os.getenv('HTTPS_PROXY')
        proxies = {}
        if http_proxy:
            proxies['http'] = http_proxy
        if https_proxy:
            proxies['https'] = https_proxy
        if proxies:
            session_kwargs['proxies'] = proxies
    
    if Config.BYPASS_SSL:
        session_kwargs['verify'] = False

    logger.info(f"Connecting to Zabbix at: {Config.ZABBIX_URL}")
    zapi = ZabbixAPI(Config.ZABBIX_URL, **session_kwargs)
    
    # Priority: Use token if available, otherwise use username/password
    if Config.ZABBIX_TOKEN:
        logger.info("Using Zabbix API token for authentication")
        zapi.login(api_token=Config.ZABBIX_TOKEN)
        logger.info("Successfully authenticated with Zabbix API token")
    else:
        if not Config.ZABBIX_USER or not Config.ZABBIX_PASSWORD:
            raise ValueError("ZABBIX_USER and ZABBIX_PASSWORD are required when ZABBIX_TOKEN is not provided")
        
        logger.info(f"Using username/password authentication for user: {Config.ZABBIX_USER}")
        zapi.login(Config.ZABBIX_USER, Config.ZABBIX_PASSWORD)
        logger.info(f"Successfully logged in to Zabbix as user: {Config.ZABBIX_USER}")
    
    return zapi
