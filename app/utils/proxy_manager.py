import requests
from enum import Enum
from typing import Dict, Optional, List
from datetime import datetime, timedelta

from app.config.app_config import AppConfig
from app.config.proxy import ProxyDetector, ProxyConfigFactory, BaseProxyConfig


class ProxyRegion(Enum):
    """代理节点地区枚举"""
    AUSTRALIA = "Australia"
    USA = "UnitedStates"
    UK = "UnitedKingdom"


class ProxyManager:
    """代理管理器，负责管理代理服务（支持多种代理软件）"""

    def __init__(self, proxy_selector="Proxy"):
        """初始化代理管理器

        Args:
            proxy_selector: 代理选择器名称，默认为"Proxy"
        """
        self.app_config = AppConfig()
        self.proxy_config_dict = self.app_config.get_proxy_config()
        self.proxy_selector = proxy_selector

        # 代理黑名单字典，记录被禁代理及禁止时间
        self.proxy_blacklist: Dict[str, datetime] = {}
        
        # 初始化代理配置实例
        self._proxy_config: Optional[BaseProxyConfig] = None
        self._initialize_proxy_config()

    def _initialize_proxy_config(self):
        """初始化代理配置，支持自动检测和回退机制"""
        try:
            # 获取配置中的优先级列表
            priority_list = self.proxy_config_dict.get('priority', ['clash_verge', 'clash_for_windows'])
            
            # 尝试创建最佳可用代理配置
            self._proxy_config = ProxyConfigFactory.create_best_available_proxy_config(priority_list)
            
            if not self._proxy_config:
                # 如果自动检测失败，使用回退配置
                fallback_config = self.proxy_config_dict.get('fallback', {})
                if fallback_config.get('enable', True):
                    self._proxy_config = ProxyConfigFactory.create_proxy_config_with_fallback(
                        preferred_type=priority_list[0] if priority_list else 'clash_verge',
                        fallback_config=fallback_config
                    )
            
            if self._proxy_config:
                print(f"使用代理配置: {self._proxy_config.proxy_type}")
            else:
                print("警告: 无法初始化任何代理配置，代理功能可能不可用")
                
        except Exception as e:
            print(f"初始化代理配置失败: {e}")
            # 尝试使用传统配置作为最后回退
            self._initialize_legacy_config()

    def _initialize_legacy_config(self):
        """使用传统配置初始化（向后兼容）"""
        try:
            legacy_config = {
                'host': self.proxy_config_dict.get('host', '127.0.0.1'),
                'port': self.proxy_config_dict.get('port', 7890),
                'api_port': self.proxy_config_dict.get('api_port', 9097),
                'secret': self.proxy_config_dict.get('secret', ''),
                'enable': self.proxy_config_dict.get('enable', True)
            }
            self._proxy_config = ProxyConfigFactory.create_proxy_config_with_fallback(
                preferred_type='clash_for_windows',
                fallback_config=legacy_config
            )
            print("使用传统代理配置")
        except Exception as e:
            print(f"传统代理配置初始化也失败: {e}")

    def get_current_config(self) -> Optional[Dict]:
        """获取当前代理配置"""
        if self._proxy_config:
            return self._proxy_config.get_config()
        return None

    def get_proxy_api_url(self) -> str:
        """获取代理API基本URL"""
        config = self.get_current_config()
        if not config:
            return "http://127.0.0.1:9097"  # 默认值
        return f'http://{config["host"]}:{config["api_port"]}'

    def get_proxy_url(self) -> str:
        """获取用于HTTP请求的代理URL"""
        config = self.get_current_config()
        if not config:
            return "http://127.0.0.1:7890"  # 默认值
        return f'http://{config["host"]}:{config["proxy_port"]}'

    def get_proxy_headers(self) -> Dict:
        """获取API请求的认证头"""
        config = self.get_current_config()
        headers = {"content-type": "application/json"}
        if config and config.get("secret"):
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

    def refresh_proxy_config(self) -> Optional[Dict]:
        """刷新代理配置（端口可能已变化）"""
        if self._proxy_config:
            return self._proxy_config.refresh_config()
        return None

    def get_proxies_for_requests(self, enable=True) -> Optional[Dict]:
        """获取用于requests的proxies字典"""
        if not enable:
            return None

        config = self.get_current_config()
        if not config:
            return None
            
        return {
            'http': f'http://{config["host"]}:{config["proxy_port"]}',
            'https': f'http://{config["host"]}:{config["proxy_port"]}'
        }
    
    def switch_proxy_software(self, proxy_type: str) -> bool:
        """切换到指定类型的代理软件
        
        Args:
            proxy_type: 代理类型 ('clash_verge', 'clash_for_windows', 等)
            
        Returns:
            切换是否成功
        """
        try:
            new_proxy_config = ProxyConfigFactory.create_proxy_config(proxy_type)
            if new_proxy_config and new_proxy_config.is_available():
                self._proxy_config = new_proxy_config
                print(f"成功切换到代理软件: {proxy_type}")
                return True
            else:
                print(f"代理软件 {proxy_type} 不可用")
                return False
        except Exception as e:
            print(f"切换代理软件失败: {e}")
            return False
    
    def get_available_proxy_types(self) -> List[str]:
        """获取所有可用的代理软件类型"""
        priority_list = self.proxy_config_dict.get('priority', ['clash_verge', 'clash_for_windows'])
        return ProxyDetector.get_available_proxies(priority_list)
    
    def get_current_proxy_type(self) -> Optional[str]:
        """获取当前使用的代理软件类型"""
        if self._proxy_config:
            return self._proxy_config.proxy_type
        return None


if __name__ == '__main__':
    # 测试代码
    proxy_manager = ProxyManager()

    # 测试获取配置
    config = proxy_manager.get_current_config()
    if config:
        print(f"当前代理类型: {proxy_manager.get_current_proxy_type()}")
        print(f"API地址: {config['host']}:{config['api_port']}")
        print(f"代理端口: {config['proxy_port']}")
        print(f"密钥: {config['secret'] or '无'}")
        print(f"配置文件路径: {config['config_path']}")
    else:
        print("无法获取代理配置")

    # 测试可用代理类型
    available_types = proxy_manager.get_available_proxy_types()
    print(f"可用代理类型: {available_types}")

    # 测试切换代理
    if available_types:
        proxy_manager.change_proxy()