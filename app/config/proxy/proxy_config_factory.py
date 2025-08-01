from typing import Optional, List, Dict
from .base_proxy_config import BaseProxyConfig
from .proxy_detector import ProxyDetector


class ProxyConfigFactory:
    """代理配置工厂类，提供统一的代理配置创建接口"""
    
    @staticmethod
    def create_proxy_config(proxy_type: str) -> Optional[BaseProxyConfig]:
        """创建指定类型的代理配置实例
        
        Args:
            proxy_type: 代理类型标识符
            
        Returns:
            代理配置实例，如果类型不支持则返回None
        """
        if proxy_type not in ProxyDetector.PROXY_CLASSES:
            print(f"不支持的代理类型: {proxy_type}")
            return None
        
        try:
            proxy_class = ProxyDetector.PROXY_CLASSES[proxy_type]
            return proxy_class()
        except Exception as e:
            print(f"创建{proxy_type}配置实例失败: {e}")
            return None
    
    @staticmethod
    def create_best_available_proxy_config(priority_list: Optional[List[str]] = None) -> Optional[BaseProxyConfig]:
        """创建最佳可用代理配置实例
        
        Args:
            priority_list: 代理优先级列表
            
        Returns:
            最佳可用代理配置实例，如果没有可用代理则返回None
        """
        best_proxy_type = ProxyDetector.get_first_available_proxy(priority_list)
        if not best_proxy_type:
            print("未找到可用的代理软件")
            return None
        
        return ProxyConfigFactory.create_proxy_config(best_proxy_type)
    
    @staticmethod
    def create_proxy_config_with_fallback(
        preferred_type: str, 
        fallback_config: Optional[Dict] = None
    ) -> Optional[BaseProxyConfig]:
        """创建代理配置实例，支持回退机制
        
        Args:
            preferred_type: 首选代理类型
            fallback_config: 回退配置字典
            
        Returns:
            代理配置实例
        """
        # 尝试创建首选代理配置
        proxy_config = ProxyConfigFactory.create_proxy_config(preferred_type)
        if proxy_config and proxy_config.is_available():
            return proxy_config
        
        # 如果首选代理不可用，尝试其他可用代理
        proxy_config = ProxyConfigFactory.create_best_available_proxy_config()
        if proxy_config:
            return proxy_config
        
        # 如果所有代理都不可用，创建回退配置代理
        if fallback_config:
            return FallbackProxyConfig(fallback_config)
        
        return None
    
    @staticmethod
    def get_all_available_configs() -> Dict[str, BaseProxyConfig]:
        """获取所有可用代理的配置实例
        
        Returns:
            代理配置实例字典，格式为 {proxy_type: config_instance}
        """
        available_proxies = ProxyDetector.get_available_proxies()
        configs = {}
        
        for proxy_type in available_proxies:
            config = ProxyConfigFactory.create_proxy_config(proxy_type)
            if config:
                configs[proxy_type] = config
        
        return configs


class FallbackProxyConfig(BaseProxyConfig):
    """回退代理配置类，用于手动配置的代理设置"""
    
    def __init__(self, fallback_config: Dict):
        """初始化回退代理配置
        
        Args:
            fallback_config: 回退配置字典
        """
        super().__init__()
        self._fallback_config = fallback_config
        self.config = self._normalize_fallback_config(fallback_config)
    
    @property
    def proxy_type(self) -> str:
        return "fallback"
    
    @property
    def default_config_paths(self) -> List:
        return []
    
    def is_available(self) -> bool:
        """回退配置始终可用"""
        return True
    
    def get_config_file_path(self) -> Optional:
        """回退配置没有配置文件"""
        return None
    
    def parse_config_file(self, config_path) -> Dict:
        """回退配置不需要解析文件"""
        return self.config
    
    def _normalize_fallback_config(self, fallback_config: Dict) -> Dict:
        """标准化回退配置格式"""
        return {
            'host': fallback_config.get('host', '127.0.0.1'),
            'api_port': fallback_config.get('api_port', 9090),
            'proxy_port': fallback_config.get('port', 7890),
            'secret': fallback_config.get('secret', ''),
            'config_path': 'fallback_config'
        }