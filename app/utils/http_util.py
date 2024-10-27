from enum import Enum

import requests
from requests.exceptions import RequestException
import time
import random
from bs4 import BeautifulSoup
from typing import Optional, Dict, List

from app.config.app_config import AppConfig
from app.config.log_config import debug, info, warning, error, critical
""""""
import os
os.environ["http_proxy"] = "http://127.0.0.1:7890"
os.environ["https_proxy"] = "http://127.0.0.1:7890"

class ProxyRegion(Enum):
    AUSTRALIA = "Australia"
    USA = "UnitedStates"
    UK = "UnitedKingdom"


class HttpUtil:
    def __init__(self):
        self.config = AppConfig()
        self.scraper = self.config.get_web_scraper_config()
        self.base_url = self.scraper.get('javdb_url', "https://javdb.com")
        self.user_agent = self.scraper.get('user_agent', "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3")
        self.timeout_seconds = self.scraper.get('timeout_seconds', 120)
        self.retry_attempts = self.scraper.get('retry_attempts', 3)

        self.proxy_config = self.config.get_proxy_config()

        self.proxy_enabled = self.proxy_config.get('enable', True)
        self.proxy_host = self.proxy_config.get('host', "127.0.0.1")
        self.proxy_port = self.proxy_config.get('port', 7890)
        self.proxy_api_port = self.proxy_config.get('api_port', 59078)
        self.proxy_secret = self.proxy_config.get('secret', "eb1dd2b3-975d-423f-81c9-3ee7e0551c31")
        self.proxy_selector = self.proxy_config.get('selector', "Proxy")

        self.proxy_headers = {
            "content-type": "application/json",
            'Authorization': f'Bearer {self.proxy_secret}'
        }

    def request(self, url: str, proxy_enable: bool = True, cookie: str = '',
                retry_count: int = 1, max_retry_count: int = None, print_content: bool = False) -> Optional[BeautifulSoup]:
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

        proxies = {'http': f'{self.proxy_host}:{self.proxy_port}', 'https': f'{self.proxy_host}:{self.proxy_port}'} if proxy_enable else None
        max_retry_count = max_retry_count or self.retry_attempts or 3
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

                self.change_proxy()
                time.sleep(random.randint(20, 60))
        error(f"达到最大重试次数 ({max_retry_count})，URL: {url}")
        raise Exception(f"请求失败，URL: {url}")




    def change_proxy_old(self):

        headers_secret = {
            'Authorization': f'Bearer {self.proxy_secret}'
        }

        # 获取所有代理
        all_proxies_info = requests.get(f'http://{self.proxy_host}:{self.proxy_api_port}/proxies', headers=headers_secret).json()
        # 获取单个代理信息
        one_proxies_url = f'http://{self.proxy_host}:{self.proxy_api_port}/proxies/{self.proxy_selector}'
        select_proxies = requests.get(one_proxies_url, headers=headers_secret).json()

        now_proxy = select_proxies['now']
        print(f'现在的代理是{now_proxy}')
        proxy_name_list = select_proxies['all'][2:-1]

        all_proxies_info['proxies']['Australia-AU-4-Rate:1.0']

        while True:
            random_proxy = random.choice(proxy_name_list)
            delay = all_proxies_info['proxies'][random_proxy]['history'][-1]['delay']
            if delay != 0:
                break
        print('随机选择的代理为{}'.format(random_proxy))
        data = {
            "name": random_proxy
        }
        headers = {
            "content-type": "application/json",
            'Authorization': f'Bearer {self.proxy_secret}'
        }

        res = requests.put(url=one_proxies_url, json=data, headers=headers)
        print('切换代理请求的状态码为{}'.format(res.status_code))
        if res.status_code == 204:
            print('切换代理成功！现在的代理为{}'.format(random_proxy))


    def _get_base_url(self) -> str:
        return f'http://{self.proxy_host}:{self.proxy_api_port}'

    
    def _get_all_proxies(self) -> Dict:
        url = f'{self._get_base_url()}/proxies'
        return requests.get(url, headers=self.proxy_headers).json()


    def _get_selector_proxies(self) -> Dict:
        url = f'{self._get_base_url()}/proxies/{self.proxy_selector}'
        return requests.get(url, headers=self.proxy_headers).json()


    def _is_proxy_available(self, proxy_info: Dict) -> bool:
        if not proxy_info.get('history'):
            return False
        latest_delay = proxy_info['history'][-1]['delay']
        return latest_delay != 0 and latest_delay < 2000  # 设置延迟阈值为2000ms


    def _get_region_proxies(self, proxies: Dict, region: ProxyRegion) -> List[Dict]:
        """获取指定地区的所有代理并按延迟排序"""
        region_proxies = []
        for name, info in proxies['proxies'].items():
            if region.value in name:
                if self._is_proxy_available(info):
                    delay = info['history'][-1]['delay']
                    region_proxies.append({
                        'name': name,
                        'delay': delay
                    })
        return sorted(region_proxies, key=lambda x: x['delay'])


    def _switch_proxy(self, proxy_name: str) -> bool:
        url = f'{self._get_base_url()}/proxies/{self.proxy_selector}'
        data = {"name": proxy_name}
        response = requests.put(url, json=data, headers=self.proxy_headers)
        return response.status_code == 204


    def get_best_available_proxy(self) -> Optional[str]:
        """按优先级顺序获取最佳可用代理"""
        all_proxies = self._get_all_proxies()
        current_proxy = self._get_selector_proxies()
        print(f'当前代理: {current_proxy["now"]}')

        # 按优先级顺序检查各地区代理
        priority_regions = [
            ProxyRegion.AUSTRALIA,
            ProxyRegion.USA,
            ProxyRegion.UK
        ]

        for region in priority_regions:
            region_proxies = self._get_region_proxies(all_proxies, region)
            if region_proxies:
                best_proxy = region_proxies[0]
                print(f'找到{region.value}地区最佳代理: {best_proxy["name"]} (延迟: {best_proxy["delay"]}ms)')
                return best_proxy['name']

        return None


    def change_proxy(self) -> bool:
        """切换到最佳可用代理"""


        best_proxy = self.get_best_available_proxy()
        if not best_proxy:
            print("未找到可用代理")
            return False

        if self._switch_proxy(best_proxy):
            print(f'成功切换到代理: {best_proxy}')
            return True
        else:
            print(f'切换代理失败: {best_proxy}')
            return False

if __name__ == '__main__':
    HttpUtil().change_proxy()