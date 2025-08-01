from typing import List, Optional, Dict, Type
from .base_proxy_config import BaseProxyConfig
from .clash_verge_config import ClashVergeConfig
from .clash_for_windows_config import ClashForWindowsConfig


class ProxyDetector:
    """代理软件检测器，负责自动检测可用的代理软件"""
    
    # 注册所有支持的代理配置类
    PROXY_CLASSES: Dict[str, Type[BaseProxyConfig]] = {
        'clash_verge': ClashVergeConfig,
        'clash_for_windows': ClashForWindowsConfig,
    }
    
    @classmethod
    def get_available_proxies(cls, priority_list: Optional[List[str]] = None) -> List[str]:
        """获取所有可用的代理软件类型列表
        
        Args:
            priority_list: 检测优先级列表，如果为None则使用默认顺序
            
        Returns:
            可用代理类型列表，按优先级排序
        """
        if priority_list is None:
            priority_list = ['clash_verge', 'clash_for_windows']
        
        available_proxies = []
        
        # 按优先级检测
        for proxy_type in priority_list:
            if proxy_type in cls.PROXY_CLASSES:
                if cls.is_proxy_available(proxy_type):
                    available_proxies.append(proxy_type)
        
        # 检测其他未在优先级列表中的代理
        for proxy_type in cls.PROXY_CLASSES:
            if proxy_type not in priority_list:
                if cls.is_proxy_available(proxy_type):
                    available_proxies.append(proxy_type)
        
        return available_proxies
    
    @classmethod
    def is_proxy_available(cls, proxy_type: str) -> bool:
        """检测指定类型的代理是否可用
        
        Args:
            proxy_type: 代理类型标识符
            
        Returns:
            是否可用
        """
        if proxy_type not in cls.PROXY_CLASSES:
            return False
            
        try:
            proxy_config = cls.PROXY_CLASSES[proxy_type]()
            return proxy_config.is_available()
        except Exception:
            return False
    
    @classmethod
    def get_first_available_proxy(cls, priority_list: Optional[List[str]] = None) -> Optional[str]:
        """获取第一个可用的代理软件类型
        
        Args:
            priority_list: 检测优先级列表
            
        Returns:
            第一个可用的代理类型，如果没有可用代理则返回None
        """
        available_proxies = cls.get_available_proxies(priority_list)
        return available_proxies[0] if available_proxies else None
    
    @classmethod
    def get_proxy_info(cls, proxy_type: str) -> Optional[Dict]:
        """获取指定代理的详细信息
        
        Args:
            proxy_type: 代理类型标识符
            
        Returns:
            代理配置信息字典，如果获取失败则返回None
        """
        if proxy_type not in cls.PROXY_CLASSES:
            return None
            
        try:
            proxy_config = cls.PROXY_CLASSES[proxy_type]()
            config_info = proxy_config.get_config()
            if config_info:
                config_info['proxy_type'] = proxy_type
            return config_info
        except Exception as e:
            print(f"获取{proxy_type}配置信息失败: {e}")
            return None
    
    @classmethod
    def register_proxy_class(cls, proxy_type: str, proxy_class: Type[BaseProxyConfig]):
        """注册新的代理配置类（用于扩展支持新的代理软件）
        
        Args:
            proxy_type: 代理类型标识符
            proxy_class: 代理配置类
        """
        cls.PROXY_CLASSES[proxy_type] = proxy_class
    
    @classmethod
    def get_all_proxy_info(cls, priority_list: Optional[List[str]] = None) -> Dict[str, Dict]:
        """获取所有可用代理的详细信息
        
        Args:
            priority_list: 检测优先级列表
            
        Returns:
            代理信息字典，格式为 {proxy_type: config_info}
        """
        available_proxies = cls.get_available_proxies(priority_list)
        proxy_info = {}
        
        for proxy_type in available_proxies:
            info = cls.get_proxy_info(proxy_type)
            if info:
                proxy_info[proxy_type] = info
        
        return proxy_info