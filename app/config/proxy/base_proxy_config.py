import os
import yaml
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Optional, List
from datetime import datetime


class BaseProxyConfig(ABC):
    """代理配置抽象基类，定义所有代理软件配置的统一接口"""
    
    def __init__(self):
        """初始化代理配置基类"""
        self.config = None
        self.last_refresh_time = None
        self.refresh_interval = 300  # 5分钟刷新间隔
    
    @property
    @abstractmethod
    def proxy_type(self) -> str:
        """返回代理类型标识符"""
        pass
    
    @property
    @abstractmethod
    def default_config_paths(self) -> List[Path]:
        """返回该代理软件的默认配置文件路径列表（按优先级排序）"""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """检查该代理软件是否可用（进程运行中或配置文件存在）"""
        pass
    
    @abstractmethod
    def get_config_file_path(self) -> Optional[Path]:
        """获取配置文件路径，优先自动检测，如果失败返回None"""
        pass
    
    @abstractmethod
    def parse_config_file(self, config_path: Path) -> Dict:
        """解析配置文件，返回标准格式的配置字典
        
        返回格式:
        {
            'host': '127.0.0.1',
            'api_port': 9090,        # API控制端口
            'proxy_port': 7890,      # 代理端口  
            'secret': 'xxx',         # API密钥
            'config_path': '/path/to/config'
        }
        """
        pass
    
    def get_config(self, force_refresh: bool = False) -> Optional[Dict]:
        """获取代理配置，自动刷新机制"""
        now = datetime.now()
        
        if (force_refresh or 
                not self.config or 
                not self.last_refresh_time or 
                (now - self.last_refresh_time).total_seconds() > self.refresh_interval):
            return self.refresh_config()
        
        return self.config
    
    def refresh_config(self) -> Optional[Dict]:
        """刷新配置信息"""
        config_path = self.get_config_file_path()
        if not config_path:
            return None
            
        try:
            self.config = self.parse_config_file(config_path)
            self.last_refresh_time = datetime.now()
            return self.config
        except Exception as e:
            print(f"刷新{self.proxy_type}配置失败: {e}")
            return None
    
    def _load_yaml_config(self, config_path: Path) -> Dict:
        """通用的YAML配置文件加载方法"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            raise ValueError(f"配置文件{config_path}解析失败: {e}")
    
    def _get_user_home(self) -> Path:
        """获取用户主目录"""
        return Path.home()
    
    def _expand_user_path(self, path_template: str) -> Path:
        """展开包含用户变量的路径模板"""
        if '{user}' in path_template:
            username = os.environ.get('USERNAME') or os.environ.get('USER', 'unknown')
            path_template = path_template.replace('{user}', username)
        return Path(os.path.expanduser(path_template))