# app_config.py
import os
from app.config.base_config import BaseConfig
from app.config.variable_resolver import VariableResolver


class AppConfig(BaseConfig):
    """应用配置类
    
    配置策略：
    - 开发环境(dev/test)：直接使用YAML配置
    - 生产环境(prod)：使用环境变量替换YAML中的敏感信息
    """
    
    def __init__(self):
        super().__init__()
        self._load_config('app')
        
        # 仅在生产环境解析环境变量
        if self._is_production():
            self.config = VariableResolver.resolve_config(self.config)
    
    def _is_production(self) -> bool:
        """判断是否为生产环境"""
        env = os.getenv('APP_ENV', 'dev')
        return env == 'prod'

    def get_database_config(self): 
        return self.config['database']
    
    def get_redis_config(self): 
        return self.config['redis']
    
    def get_jellyfin_config(self): 
        return self.config['jellyfin']
    
    def get_everything_config(self): 
        return self.config['everything']
    
    def get_download_client_config(self): 
        return self.config['download_client']
    
    def get_web_scraper_config(self): 
        return self.config['web_scraper']
    
    def get_proxy_config(self): 
        return self.get_web_scraper_config()['proxy']
    
    def get_chart_config(self): 
        return self.config['chart']
    
    def get_chart_type_config(self): 
        return self.get_chart_config()['chart_type']
    
    def get_app_config(self): 
        return self.config['app']

