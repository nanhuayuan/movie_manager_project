import requests
from requests.exceptions import RequestException
import time
import random
from bs4 import BeautifulSoup
from typing import Optional

from app.config.app_config import AppConfig
from app.config.log_config import debug, info, warning, error, critical
""""""
import os
os.environ["http_proxy"] = "http://127.0.0.1:7890"
os.environ["https_proxy"] = "http://127.0.0.1:7890"

class HttpUtil:
    def __init__(self):
        config = AppConfig().get_web_scraper_config()
        self.base_url = config['javdb_url']
        self.user_agent = config['user_agent']
        self.timeout_seconds = config.get('timeout_seconds', 10)
        self.retry_attempts = config.get('retry_attempts', 3)
        self.proxy_enabled = config.get('proxy_enabled', True)
        self.proxy_url = config.get('proxy_url', "http://127.0.0.1:7890")

    def request(self, url: str, proxy_enable: bool = True, cookie: str = '',
                retry_count: int = 1, max_retry_count: int = 3, print_content: bool = False) -> Optional[BeautifulSoup]:
        """
        发送HTTP请求并返回解析后的BeautifulSoup对象。

        Args:
            url (str): 请求的URL。
            proxy_enable (bool): 是否启用代理。
            cookie (str): 请求的Cookie。
            retry_count (int): 当前重试次数。
            max_retry_count (int): 最大重试次数。
            print_content (bool): 是否打印响应内容。

        Returns:
            Optional[BeautifulSoup]: 解析后的BeautifulSoup对象，如果请求失败则返回None。
        """
        debug(f"正在请求URL: {url}")
        headers = {
            'User-Agent': self.user_agent,
        }
        if cookie:
            headers['Cookie'] = cookie

        proxies = {'http': self.proxy_url, 'https': self.proxy_url} if proxy_enable else None

        while retry_count <= max_retry_count:
            try:
                response = requests.get(url=url, headers=headers, proxies=proxies, timeout=self.timeout_seconds)
                response.raise_for_status()
                content = response.text
                if print_content:
                    debug(f"响应内容: {content}")
                return BeautifulSoup(content, 'lxml')
            except RequestException as e:
                warning(f"请求失败 (尝试 {retry_count}/{max_retry_count}): {e}")
                retry_count += 1
                time.sleep(random.randint(1, 5))

        error(f"达到最大重试次数 ({max_retry_count})，URL: {url}")
        raise Exception(f"请求失败，URL: {url}")