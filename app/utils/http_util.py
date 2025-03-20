import sys
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
from datetime import datetime, timedelta

#os.environ["http_proxy"] = "http://127.0.0.1:7890"
#os.environ["https_proxy"] = "http://127.0.0.1:7890"

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

        # 代理黑名单字典，记录被禁代理及禁止时间
        self.proxy_blacklist: Dict[str, datetime] = {}

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
        return latest_delay != 0 and latest_delay < 2000

    def _is_proxy_blacklisted(self, proxy_name: str) -> bool:
        """检查代理是否被禁并清理过期黑名单"""
        if proxy_name in self.proxy_blacklist:
            # 如果距离被禁超过3天，自动解禁
            if datetime.now() - self.proxy_blacklist[proxy_name] > timedelta(days=3):
                del self.proxy_blacklist[proxy_name]
                return False
            return True
        return False

    def _get_region_proxies(self, proxies: Dict, region: ProxyRegion) -> List[Dict]:
        """获取指定地区的可用代理并按延迟排序"""
        region_proxies = []
        for name, info in proxies['proxies'].items():
            if region.value in name and not self._is_proxy_blacklisted(name):
                if self._is_proxy_available(info):
                    delay = info['history'][-1]['delay']
                    region_proxies.append({
                        'name': name,
                        'delay': delay
                    })
        return sorted(region_proxies, key=lambda x: x['delay'])

    def get_best_available_proxy(self) -> Optional[str]:
        """按优先级获取最佳可用代理"""
        all_proxies = self._get_all_proxies()

        # 优先级地区
        priority_regions = [
            ProxyRegion.AUSTRALIA,
            ProxyRegion.USA,
            ProxyRegion.UK
        ]

        for region in priority_regions:
            region_proxies = self._get_region_proxies(all_proxies, region)
            if region_proxies:
                best_proxy = region_proxies[0]['name']
                print(f'找到{region.value}地区最佳代理: {best_proxy}')
                return best_proxy

        return None

    def _switch_proxy(self, proxy_name: str) -> bool:
        url = f'{self._get_base_url()}/proxies/{self.proxy_selector}'
        data = {"name": proxy_name}
        response = requests.put(url, json=data, headers=self.proxy_headers)
        return response.status_code == 204

    def change_proxy(self) -> bool:
        """切换到最佳可用代理"""
        # 标记当前代理为黑名单
        current_proxy = self._get_selector_proxies()['now']
        self.proxy_blacklist[current_proxy] = datetime.now()

        best_proxy = self.get_best_available_proxy()
        if not best_proxy:
            print("无可用代理")
            return False

        if self._switch_proxy(best_proxy):
            print(f'成功切换到代理: {best_proxy}')
            return True
        else:
            print(f'切换代理失败: {best_proxy}')
            return False

    def local_request(self, url: str, cookie: str = '', print_content: bool = False) -> Optional[BeautifulSoup]:
        """专门用于内网请求，不使用代理"""
        return self.request(url, proxy_enable=False, cookie=cookie, print_content=print_content)

    def request(self, url: str, proxy_enable: bool = True,
                cookie: str = '', print_content: bool = False) -> Optional[BeautifulSoup]:
        """发送HTTP请求并处理代理"""
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36',
        }
        if cookie:
            headers['Cookie'] = cookie

        # 判断是否为内网地址
        is_local_network = any([
            url.startswith('http://localhost'),
            url.startswith('https://localhost'),
            url.startswith('http://127.'),
            url.startswith('https://127.'),
            url.startswith('http://192.168.'),
            url.startswith('https://192.168.')
        ])

        # 内网地址默认不走代理，除非特别指定
        use_proxy = proxy_enable and not is_local_network

        # 设置请求级别的代理，不影响全局环境变量
        proxies = None
        if use_proxy:
            proxies = {
                'http': f'http://{self.proxy_host}:{self.proxy_port}',
                'https': f'http://{self.proxy_host}:{self.proxy_port}'
            }

        # 请求时打印代理状态
        if print_content:
            print(f"请求URL: {url}, 使用代理: {'是' if proxies else '否'}")

        while True:
            try:
                # 通过proxies参数控制是否使用代理，不影响全局设置
                response = requests.get(url=url, headers=headers, proxies=proxies, timeout=120)
                response.raise_for_status()

                if print_content:
                    print(f"响应内容: {response.text}")

                soup = BeautifulSoup(response.text, 'lxml')
                banned = "The owner of this website has banned your access based on your browser's behaving"

                if banned in soup.get_text("|", strip=True):
                    # 如果被禁，切换代理并重试
                    proxy_change_success = self.change_proxy()
                    if not proxy_change_success:
                        print("所有代理均已被禁，程序停止")
                        sys.exit(0)
                    continue

                return soup

            except RequestException as e:
                print(f"请求失败，错误: {e}")
                if use_proxy:
                    proxy_change_success = self.change_proxy()
                    if not proxy_change_success:
                        print("无法切换到可用代理，程序停止")
                        return None
                    time.sleep(random.randint(20, 60))
                else:
                    # 如果不使用代理但请求失败，直接返回None
                    print("不使用代理的请求失败，不进行重试")
                    return None
    def request_old(self, url: str, proxy_enable: bool = True,
                cookie: str = '', print_content: bool = False) -> Optional[BeautifulSoup]:
        """发送HTTP请求并处理代理"""
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36',
        }
        if cookie:
            headers['Cookie'] = cookie

        proxies = {'http': f'{self.proxy_host}:{self.proxy_port}',
                   'https': f'{self.proxy_host}:{self.proxy_port}'} if proxy_enable else None

        while True:
            try:
                response = requests.get(url=url, headers=headers, proxies=proxies, timeout=120)
                response.raise_for_status()

                if print_content:
                    print(f"响应内容: {response.text}")

                soup = BeautifulSoup(response.text, 'lxml')
                banned = "The owner of this website has banned your access based on your browser's behaving"

                if banned in soup.get_text("|", strip=True):
                    # 如果被禁，切换代理并重试
                    proxy_change_success = self.change_proxy()
                    if not proxy_change_success:
                        print("所有代理均已被禁，程序停止")
                        #raise Exception(f"请求失败，URL: {url}")
                        sys.exit(0)
                    continue

                return soup

            except RequestException as e:
                print(f"请求失败，错误: {e}")
                proxy_change_success = self.change_proxy()
                if not proxy_change_success:
                    print("无法切换到可用代理，程序停止")
                    return None
                time.sleep(random.randint(20, 60))


if __name__ == '__main__':
    HttpUtil().change_proxy()