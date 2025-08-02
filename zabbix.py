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

    def _is_token_expired(self, e):
        return 'API token expired' in str(e) or '-32500' in str(e)

    def _execute_with_retry(self, api_call, *args, **kwargs):
        try:
            return api_call(*args, **kwargs)
        except Exception as e:
            if self._is_token_expired(e):
                logger.warning("Zabbix API token expired. Re-authenticating...")
                self.zapi = self._connect()
                logger.info("Re-authentication successful. Retrying the request...")
                # Get the same method from the new zapi object and retry
                api_object_name = api_call.__self__.__class__.__name__.lower()
                method_name = api_call.__name__
                new_api_object = getattr(self.zapi, api_object_name)
                new_api_call = getattr(new_api_object, method_name)
                return new_api_call(*args, **kwargs)
            else:
                raise e

    def __getattr__(self, name):
        # Get the actual API object (e.g., zapi.problem, zapi.host)
        api_object = getattr(self.zapi, name)

        class _APIObjectWrapper:
            def __init__(self, parent_wrapper, api_obj):
                self.parent_wrapper = parent_wrapper
                self.api_obj = api_obj

            def __getattr__(self, method_name):
                api_call = getattr(self.api_obj, method_name)
                
                def wrapper(*args, **kwargs):
                    return self.parent_wrapper._execute_with_retry(api_call, *args, **kwargs)
                
                return wrapper

        return _APIObjectWrapper(self, api_object)


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
