import sys
import requests
import time
import random
from bs4 import BeautifulSoup
from typing import Optional, Dict
from requests.exceptions import RequestException

from app.utils.proxy_manager import ProxyManager


class HttpUtil:
    def __init__(self):
        """初始化HTTP工具类"""
        # HTTP请求参数
        self.user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
        self.timeout_seconds = 120
        self.retry_attempts = 3

        # 初始化代理管理器
        self.proxy_manager = ProxyManager()

    def local_request(self, url: str, cookie: str = '', print_content: bool = False) -> Optional[BeautifulSoup]:
        """专门用于内网请求，不使用代理"""
        return self.request(url, proxy_enable=False, cookie=cookie, print_content=print_content)

    def request(self, url: str, proxy_enable: bool = True,
                cookie: str = '', print_content: bool = False) -> Optional[BeautifulSoup]:
        """发送HTTP请求并处理代理

        Args:
            url: 请求的URL
            proxy_enable: 是否启用代理
            cookie: 可选的Cookie字符串
            print_content: 是否打印响应内容

        Returns:
            BeautifulSoup对象，如果请求失败则返回None
        """
        headers = {
            'User-Agent': self.user_agent,
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

        # 获取代理设置
        proxies = self.proxy_manager.get_proxies_for_requests(use_proxy)

        # 请求时打印代理状态
        if print_content:
            print(f"请求URL: {url}, 使用代理: {'是' if proxies else '否'}")

        attempts = 0
        while attempts < self.retry_attempts:
            try:
                # 通过proxies参数控制是否使用代理，不影响全局设置
                response = requests.get(
                    url=url,
                    headers=headers,
                    proxies=proxies,
                    timeout=self.timeout_seconds
                )
                response.raise_for_status()

                if print_content:
                    print(f"响应内容: {response.text}")

                soup = BeautifulSoup(response.text, 'lxml')
                banned = "The owner of this website has banned your access based on your browser's behaving"

                if banned in soup.get_text("|", strip=True):
                    # 如果被禁，切换代理并重试
                    proxy_change_success = self.proxy_manager.change_proxy()
                    if not proxy_change_success:
                        print("所有代理均已被禁，程序停止")
                        sys.exit(0)

                    # 更新代理设置
                    proxies = self.proxy_manager.get_proxies_for_requests(use_proxy)
                    attempts += 1
                    continue

                return soup

            except RequestException as e:
                print(f"请求失败，错误: {e}")
                attempts += 1

                if use_proxy:
                    # 尝试刷新Clash配置（端口可能已变化）
                    self.proxy_manager.refresh_clash_config()

                    # 切换代理
                    proxy_change_success = self.proxy_manager.change_proxy()
                    if not proxy_change_success:
                        print("无法切换到可用代理")
                        if attempts >= self.retry_attempts:
                            print("已达最大重试次数，返回None")
                            return None

                    # 更新代理设置
                    proxies = self.proxy_manager.get_proxies_for_requests(use_proxy)

                    # 随机延迟，避免请求过于频繁
                    time.sleep(random.randint(5, 15))
                else:
                    # 如果不使用代理但请求失败，直接返回None
                    print("不使用代理的请求失败，不进行重试")
                    return None

        # 达到最大重试次数后返回None
        print("已达最大重试次数，请求失败")
        return None


if __name__ == '__main__':
    # 测试代码
    http_util = HttpUtil()
    result = http_util.request("https://ipinfo.io/json", proxy_enable=True, print_content=True)
    if result:
        print("请求成功!")
        print(result.text)
    else:
        print("请求失败!")