import os
from zabbix_api import ZabbixAPI

def get_zabbix_api():
    zabbix_url = os.getenv('ZABBIX_URL')
    if not zabbix_url:
        raise ValueError("Environment variable 'ZABBIX_URL' is not set.")

    use_proxy = os.getenv('USE_PROXY', 'false').lower() == 'true'
    bypass_ssl = os.getenv('BYPASS_SSL', 'false').lower() == 'true'

    session_kwargs = {}
    if use_proxy:
        http_proxy = os.getenv('HTTP_PROXY')
        https_proxy = os.getenv('HTTPS_PROXY')
        proxies = {}
        if http_proxy:
            proxies['http'] = http_proxy
        if https_proxy:
            proxies['https'] = https_proxy
        if proxies:
            session_kwargs['proxies'] = proxies
    
    if bypass_ssl:
        session_kwargs['verify'] = False

    zapi = ZabbixAPI(zabbix_url, **session_kwargs)
    zapi.login(os.getenv('ZABBIX_USER'), os.getenv('ZABBIX_PASSWORD'))
    return zapi
