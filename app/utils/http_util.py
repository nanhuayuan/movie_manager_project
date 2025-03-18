import sys
from enum import Enum
import os
import yaml
from pathlib import Path
import requests
from requests.exceptions import RequestException
import time
import random
from bs4 import BeautifulSoup
from typing import Optional, Dict, List

from app.config.app_config import AppConfig
from app.config.log_config import debug, info, warning, error, critical

""""""
from datetime import datetime, timedelta


class ProxyRegion(Enum):
    AUSTRALIA = "Australia"
    USA = "UnitedStates"
    UK = "UnitedKingdom"


class HttpUtil:
    def __init__(self):
        self.config = AppConfig()
        self.scraper = self.config.get_web_scraper_config()
        self.base_url = self.scraper.get('javdb_url', "https://javdb.com")
        self.user_agent = self.scraper.get('user_agent',
                                           "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3")
        self.timeout_seconds = self.scraper.get('timeout_seconds', 120)
        self.retry_attempts = self.scraper.get('retry_attempts', 3)

        # 初始化代理配置
        self._init_proxy_config()

        # 代理黑名单字典，记录被禁代理及禁止时间
        self.proxy_blacklist: Dict[str, datetime] = {}

    def _init_proxy_config(self):
        """初始化代理配置，优先尝试从Clash配置文件获取，失败则使用AppConfig"""
        try:
            # 尝试从Clash配置文件获取
            clash_config = self._get_clash_config()
            self.proxy_enabled = True
            self.proxy_host = clash_config.get('host', "127.0.0.1")
            self.proxy_port = clash_config.get('port', 7890)
            self.proxy_api_port = clash_config.get('port', 7890)  # API端口与代理端口相同
            self.proxy_secret = clash_config.get('secret', "")
            self.proxy_selector = "Proxy"  # 默认选择器名称

            info(f"已从Clash配置文件加载代理设置: {self.proxy_host}:{self.proxy_port}")
        except Exception as e:
            # 如果获取失败，回退到AppConfig配置
            warning(f"从Clash配置加载失败: {str(e)}，使用AppConfig配置")
            self.proxy_config = self.config.get_proxy_config()
            self.proxy_enabled = self.proxy_config.get('enable', True)
            self.proxy_host = self.proxy_config.get('host', "127.0.0.1")
            self.proxy_port = self.proxy_config.get('port', 7890)
            self.proxy_api_port = self.proxy_config.get('api_port', 59078)
            self.proxy_secret = self.proxy_config.get('secret', "eb1dd2b3-975d-423f-81c9-3ee7e0551c31")
            self.proxy_selector = self.proxy_config.get('selector', "Proxy")

        # 设置代理API请求头
        self.proxy_headers = {
            "content-type": "application/json"
        }
        if self.proxy_secret:
            self.proxy_headers['Authorization'] = f'Bearer {self.proxy_secret}'

    def _find_clash_config_path(self):
        """查找Clash配置文件路径（支持Windows和跨平台）"""
        # Windows默认路径（Clash for Windows）
        if 'USERPROFILE' in os.environ:
            win_path = Path(os.environ['USERPROFILE']) / 'AppData/Roaming/Clash for Windows/Profiles'
            if win_path.exists():
                for file in win_path.iterdir():
                    if file.suffix in ('.yaml', '.yml') and file.name.startswith('config'):
                        return file

        # 通用路径尝试
        paths = [
            Path.home() / ".config/clash/config.yaml",  # Linux/macOS
            Path(os.getcwd()) / "config.yaml"  # 当前目录
        ]

        for p in paths:
            if p.exists():
                return p

        raise FileNotFoundError("Clash配置文件未找到")

    def _get_clash_config(self):
        """解析Clash配置文件获取API信息"""
        config_path = self._find_clash_config_path()

        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
        except Exception as e:
            raise ValueError(f"配置文件解析失败: {str(e)}")

        # 获取监听地址和密钥
        controller = config.get('external-controller', '')
        secret = config.get('secret', '')

        if not controller:
            raise ValueError("配置文件中缺少external-controller配置")

        # 解析端口
        if ':' in controller:
            _, port = controller.split(':', 1)
            port = int(port)
        else:
            port = 7890  # 默认端口

        return {
            'host': '127.0.0.1',
            'port': port,
            'secret': secret.strip() if secret else None,
            'config_path': str(config_path)
        }

    def refresh_proxy_config(self):
        """刷新代理配置（适用于Clash重启后调用）"""
        try:
            self._init_proxy_config()
            info("代理配置已刷新")
            return True
        except Exception as e:
            error(f"刷新代理配置失败: {str(e)}")
            return False

    def _get_base_url(self) -> str:
        return f'http://{self.proxy_host}:{self.proxy_api_port}'

    def _get_all_proxies(self) -> Dict:
        try:
            url = f'{self._get_base_url()}/proxies'
            response = requests.get(url, headers=self.proxy_headers, timeout=5)
            if response.status_code != 200:
                error(f"获取代理列表失败，状态码: {response.status_code}")
                return {"proxies": {}}
            return response.json()
        except Exception as e:
            error(f"获取代理列表异常: {str(e)}")
            # 尝试刷新配置
            self.refresh_proxy_config()
            return {"proxies": {}}

    def _get_selector_proxies(self) -> Dict:
        try:
            url = f'{self._get_base_url()}/proxies/{self.proxy_selector}'
            response = requests.get(url, headers=self.proxy_headers, timeout=5)
            if response.status_code != 200:
                return {"now": ""}
            return response.json()
        except Exception as e:
            error(f"获取选择器代理异常: {str(e)}")
            return {"now": ""}

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
                info(f'找到{region.value}地区最佳代理: {best_proxy}')
                return best_proxy

        return None

    def _switch_proxy(self, proxy_name: str) -> bool:
        url = f'{self._get_base_url()}/proxies/{self.proxy_selector}'
        data = {"name": proxy_name}
        try:
            response = requests.put(url, json=data, headers=self.proxy_headers, timeout=5)
            return response.status_code == 204
        except Exception as e:
            error(f"切换代理异常: {str(e)}")
            return False

    def change_proxy(self) -> bool:
        """切换到最佳可用代理"""
        try:
            # 标记当前代理为黑名单
            current_proxy = self._get_selector_proxies().get('now', '')
            if current_proxy:
                self.proxy_blacklist[current_proxy] = datetime.now()

            best_proxy = self.get_best_available_proxy()
            if not best_proxy:
                warning("无可用代理")
                return False

            if self._switch_proxy(best_proxy):
                info(f'成功切换到代理: {best_proxy}')
                return True
            else:
                warning(f'切换代理失败: {best_proxy}')
                return False
        except Exception as e:
            error(f"更换代理过程异常: {str(e)}")
            return False

    def local_request(self, url: str, cookie: str = '', print_content: bool = False) -> Optional[BeautifulSoup]:
        """专门用于内网请求，不使用代理"""
        return self.request(url, proxy_enable=False, cookie=cookie, print_content=print_content)

    def request(self, url: str, proxy_enable: bool = True,
                cookie: str = '', print_content: bool = False) -> Optional[BeautifulSoup]:
        """发送HTTP请求并处理代理"""
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
        use_proxy = proxy_enable and self.proxy_enabled and not is_local_network

        # 设置请求级别的代理，不影响全局环境变量
        proxies = None
        if use_proxy:
            proxies = {
                'http': f'http://{self.proxy_host}:{self.proxy_port}',
                'https': f'http://{self.proxy_host}:{self.proxy_port}'
            }

        # 请求时打印代理状态
        if print_content:
            info(f"请求URL: {url}, 使用代理: {'是' if proxies else '否'}")

        retry_count = 0
        max_retries = self.retry_attempts

        while retry_count < max_retries:
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
                    debug(f"响应内容: {response.text[:500]}...")

                soup = BeautifulSoup(response.text, 'lxml')
                banned_text = "The owner of this website has banned your access based on your browser's behaving"

                if banned_text in soup.get_text("|", strip=True):
                    warning(f"代理被网站封禁，尝试切换代理")
                    if not use_proxy or not self.change_proxy():
                        error("所有代理均已被禁或无法切换代理，请检查代理配置")
                        if retry_count >= max_retries - 1:
                            return None
                    retry_count += 1
                    time.sleep(random.randint(3, 10))
                    continue

                return soup

            except RequestException as e:
                warning(f"请求失败 ({retry_count + 1}/{max_retries})，错误: {str(e)}")
                retry_count += 1

                if use_proxy:
                    # 尝试刷新配置（可能是Clash重启导致端口变化）
                    if retry_count == 1:
                        info("尝试刷新代理配置...")
                        self.refresh_proxy_config()

                    # 尝试切换代理
                    self.change_proxy()
                    time.sleep(random.randint(2, 5))
                else:
                    # 不使用代理但请求失败，等待后重试
                    time.sleep(random.randint(1, 3))

                # 最后一次尝试失败
                if retry_count >= max_retries:
                    error(f"请求 {url} 失败，已达到最大重试次数")
                    return None


if __name__ == '__main__':
    http_util = HttpUtil()
    print(f"代理配置: {http_util.proxy_host}:{http_util.proxy_port}")
    print(f"API端口: {http_util.proxy_api_port}")

    # 测试代理切换
    current = http_util._get_selector_proxies().get('now', 'Unknown')
    print(f"当前代理: {current}")

    if http_util.change_proxy():
        new_proxy = http_util._get_selector_proxies().get('now', 'Unknown')
        print(f"切换后代理: {new_proxy}")