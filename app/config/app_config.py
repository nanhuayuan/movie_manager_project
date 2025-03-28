# app_config.py
from app.config.base_config import BaseConfig


class AppConfig(BaseConfig):
    def __init__(self):
        super().__init__()
        self._load_config('app')

    def get_database_config(self): return self.config['database']
    def get_redis_config(self): return self.config['redis']
    def get_jellyfin_config(self): return self.config['jellyfin']
    def get_everything_config(self): return self.config['everything']
    def get_download_client_config(self): return self.config['download_client']
    def get_web_scraper_config(self): return self.config['web_scraper']
    def get_proxy_config(self): return self.get_web_scraper_config()['proxy']
    def get_chart_config(self): return self.config['chart']
    def get_chart_type_config(self): return self.get_chart_config()['chart_type']
    def get_app_config(self): return self.config['app']

