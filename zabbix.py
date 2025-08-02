import os
import logging
from zabbix_api import ZabbixAPI
from config import Config

logger = logging.getLogger(__name__)

class ZabbixAPIWrapper:
    def __init__(self, url, user, password, token, session_kwargs):
        self.url = url
        self.user = user
        self.password = password
        self.token = token
        self.session_kwargs = session_kwargs
        self.zapi = self._connect()

    def _connect(self):
        logger.info(f"Connecting to Zabbix at: {self.url}")
        zapi = ZabbixAPI(self.url, **self.session_kwargs)
        
        if self.token:
            logger.info("Using Zabbix API token for authentication")
            zapi.login(api_token=self.token)
            logger.info("Successfully authenticated with Zabbix API token")
        else:
            if not self.user or not self.password:
                raise ValueError("Zabbix user and password are required when a token is not provided.")
            logger.info(f"Using username/password authentication for user: {self.user}")
            zapi.login(self.user, self.password)
            logger.info(f"Successfully logged in to Zabbix as user: {self.user}")
        return zapi

    def __getattr__(self, name):
        def wrapper(*args, **kwargs):
            try:
                # Forward the call to the actual ZabbixAPI object
                return getattr(self.zapi, name)(*args, **kwargs)
            except Exception as e:
                # Check for token expiration error
                if 'API token expired' in str(e) or ('-32500' in str(e)):
                    logger.warning("Zabbix API token expired. Re-authenticating...")
                    self.zapi = self._connect()
                    logger.info("Re-authentication successful. Retrying the request...")
                    # Retry the original call
                    return getattr(self.zapi, name)(*args, **kwargs)
                else:
                    # Re-raise other exceptions
                    raise e
        return wrapper

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

    return ZabbixAPIWrapper(
        url=Config.ZABBIX_URL,
        user=Config.ZABBIX_USER,
        password=Config.ZABBIX_PASSWORD,
        token=Config.ZABBIX_TOKEN,
        session_kwargs=session_kwargs
    )
