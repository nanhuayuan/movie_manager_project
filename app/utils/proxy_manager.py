import os
import yaml
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime
import requests
from enum import Enum


class ProxyRegion(Enum):
    AUSTRALIA = "Australia"
    USA = "UnitedStates"
    UK = "UnitedKingdom"


class ProxyManager:
    """代理管理器，负责获取Clash配置并管理代理服务"""
    
    def __init__(self, config=None):
        """初始化代理管理器
        
        Args:
            config: 可选的应用配置对象
        """
        self.config = config
        self.clash_config = None
        self.last_refresh_time = None
        # 刷新间隔（5分钟）
        self.refresh_interval = 300
        
        # 从配置文件或默认值初始化代理选择器
        self.proxy_selector = "Proxy"
        if config:
            proxy_config = getattr(config, 'get_proxy_config', lambda: {})()
            self.proxy_selector = proxy_config.get('selector', self.proxy_selector)
        
        # 代理黑名单字典，记录被禁代理及禁止时间
        self.proxy_blacklist = {}
        
        # 初始化时加载配置
        self.refresh_clash_config()
        
    def get_clash_config_path(self) -> Path:
        """自动查找Clash配置文件路径（支持Windows和跨平台）"""
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

    def parse_clash_config(self, config_path=None) -> Dict:
        """解析Clash配置文件获取API信息"""
        if not config_path:
            config_path = self.get_clash_config_path()

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

        # 解析主机和端口
        host = '127.0.0.1'  # 默认主机
        port = None
        
        if ':' in controller:
            host_part, port_part = controller.split(':', 1)
            # 如果主机部分不为空，则使用配置文件中的主机
            if host_part:
                host = host_part
            # 解析端口
            port = int(port_part)

        return {
            'host': host,
            'port': port,
            'secret': secret.strip() if secret else None,
            'config_path': str(config_path)
        }
    
    def refresh_clash_config(self) -> Dict:
        """刷新Clash配置信息"""
        self.clash_config = self.parse_clash_config()
        self.last_refresh_time = datetime.now()
        return self.clash_config
    
    def get_clash_config(self, force_refresh=False) -> Dict:
        """获取Clash配置，如果超过刷新间隔则自动刷新"""
        now = datetime.now()
        
        if (force_refresh or 
            not self.last_refresh_time or 
            (now - self.last_refresh_time).total_seconds() > self.refresh_interval):
            return self.refresh_clash_config()
            
        return self.clash_config
    
    def get_proxy_api_url(self) -> str:
        """获取Clash API基本URL"""
        config = self.get_clash_config()
        return f'http://{config["host"]}:{config["port"]}'
    
    def get_proxy_url(self) -> str:
        """获取用于HTTP请求的代理URL"""
        config = self.get_clash_config()
        return f'http://{config["host"]}:{config["port"]}'
    
    def get_proxy_headers(self) -> Dict:
        """获取API请求的认证头"""
        config = self.get_clash_config()
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
    
    def _get_region_proxies(self, proxies: Dict, region: ProxyRegion) -> list:
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
    
    def get_proxies_for_requests(self, enable=True) -> Optional[Dict]:
        """获取用于requests的proxies字典"""
        if not enable:
            return None
            
        config = self.get_clash_config()
        return {
            'http': f'http://{config["host"]}:{config["port"]}',
            'https': f'http://{config["host"]}:{config["port"]}'
        }


if __name__ == '__main__':
    # 测试代码
    proxy_manager = ProxyManager()
    config = proxy_manager.get_clash_config()
    print(f"API地址: {config['host']}:{config['port']}")
    print(f"密钥: {config['secret'] or '无'}")
    print(f"配置文件路径: {config['config_path']}")
    
    # 测试切换代理
    proxy_manager.change_proxy()
