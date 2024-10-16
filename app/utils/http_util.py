import requests
from requests.exceptions import ProxyError
import time
import random
from bs4 import BeautifulSoup
from app.utils.log_util import debug, info, warning, error, critical

class HttpUtil:
    def proxy_request(url, cookie='', retry_count=1, max_retry_count=10, print_content=False):
        """
        发送代理请求并返回解析后的BeautifulSoup对象。

        Args:
            url (str): 请求的URL。
            cookie (str, optional): 请求的Cookie。默认为空字符串。
            retry_count (int, optional): 当前重试次数。默认为1。
            max_retry_count (int, optional): 最大重试次数。默认为10。
            print_content (bool, optional): 是否打印响应内容。默认为False。

        Returns:
            BeautifulSoup: 解析后的BeautifulSoup对象。

        Raises:
            ProxyError: 如果代理请求失败且超过最大重试次数。
        """
        debug(f"Requesting URL: {url}")
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.159 Safari/537.36',
        }
        if cookie:
            headers['Cookie'] = cookie

        proxy = {
            'http': 'http://127.0.0.1:7890',
            'https': 'http://127.0.0.1:7890'
        }

        while retry_count <= max_retry_count:
            try:
                response = requests.get(url=url, headers=headers, proxies=proxy)
                response.raise_for_status()
                content = response.text
                if print_content:
                    debug(f"Response content: {content}")
                return BeautifulSoup(content, 'lxml')
            except (ProxyError, requests.RequestException) as e:
                warning(f"Request failed (attempt {retry_count}/{max_retry_count}): {e}")
                retry_count += 1
                time.sleep(random.randint(10, 30))

        raise ProxyError(f"Max retries ({max_retry_count}) exceeded for URL: {url}")