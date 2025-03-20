import requests
from enum import Enum
from typing import Dict, Optional, List
from datetime import datetime, timedelta

from app.config.clash_config import ClashConfig


class ProxyRegion(Enum):
    """代理节点地区枚举"""
    AUSTRALIA = "Australia"
    USA = "UnitedStates"
    UK = "UnitedKingdom"


class ProxyManager:
    """代理管理器，负责管理Clash代理服务"""

    def __init__(self, proxy_selector="Proxy"):
        """初始化代理管理器

        Args:
            proxy_selector: Clash中的代理选择器名称，默认为"Proxy"
        """
        self.clash_config = ClashConfig()
        self.proxy_selector = proxy_selector

        # 代理黑名单字典，记录被禁代理及禁止时间
        self.proxy_blacklist: Dict[str, datetime] = {}

    def get_proxy_api_url(self) -> str:
        """获取Clash API基本URL"""
        config = self.clash_config.get_config()
        return f'http://{config["host"]}:{config["api_port"]}'

    def get_proxy_url(self) -> str:
        """获取用于HTTP请求的代理URL"""
        config = self.clash_config.get_config()
        return f'http://{config["host"]}:{config["port"]}'

    def get_proxy_headers(self) -> Dict:
        """获取API请求的认证头"""
        config = self.clash_config.get_config()
        headers = {"content-type": "application/json"}
        if config["secret"]:
            headers["Authorization"] = f'Bearer {config["secret"]}'
        return headers

    def get_all_proxies(self) -> Dict:
        """获取所有代理信息"""
        url = f'{self.get_proxy_api_url()}/proxies'
        return requests.get(url, headers=self.get_proxy_headers()).json()

    def get_selector_proxies(self) -> Dict:
        """获取当前选择器下的代理信息"""
        url = f'{self.get_proxy_api_url()}/proxies/{self.proxy_selector}'
        return requests.get(url, headers=self.get_proxy_headers()).json()

    def _is_proxy_available(self, proxy_info: Dict) -> bool:
        """检查代理是否可用"""
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
        all_proxies = self.get_all_proxies()

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

    def switch_proxy(self, proxy_name: str) -> bool:
        """切换到指定代理"""
        url = f'{self.get_proxy_api_url()}/proxies/{self.proxy_selector}'
        data = {"name": proxy_name}
        response = requests.put(url, json=data, headers=self.get_proxy_headers())
        return response.status_code == 204

    def change_proxy(self) -> bool:
        """切换到最佳可用代理"""
        try:
            # 标记当前代理为黑名单
            current_proxy = self.get_selector_proxies()['now']
            self.proxy_blacklist[current_proxy] = datetime.now()

            best_proxy = self.get_best_available_proxy()
            if not best_proxy:
                print("无可用代理")
                return False

            if self.switch_proxy(best_proxy):
                print(f'成功切换到代理: {best_proxy}')
                return True
            else:
                print(f'切换代理失败: {best_proxy}')
                return False
        except Exception as e:
            print(f"切换代理时发生错误: {str(e)}")
            return False

    def refresh_clash_config(self) -> Dict:
        """刷新Clash配置（端口可能已变化）"""
        return self.clash_config.refresh_config()

    def get_proxy_api_url(self) -> str:
        """获取Clash API基本URL"""
        config = self.clash_config.get_config()
        return f'http://{config["host"]}:{config["api_port"]}'

    def get_proxies_for_requests(self, enable=True) -> Optional[Dict]:
        """获取用于requests的proxies字典"""
        if not enable:
            return None

        config = self.clash_config.get_config()
        return {
            'http': f'http://{config["host"]}:{config["proxy_port"]}',
            'https': f'http://{config["host"]}:{config["proxy_port"]}'
        }


if __name__ == '__main__':
    # 测试代码
    proxy_manager = ProxyManager()

    # 测试获取配置
    config = proxy_manager.clash_config.get_config()
    print(f"API地址: {config['host']}:{config['api_port']}")
    print(f"代理端口: {config['proxy_port']}")
    print(f"密钥: {config['secret'] or '无'}")
    print(f"配置文件路径: {config['config_path']}")

    # 测试切换代理
    proxy_manager.change_proxy()