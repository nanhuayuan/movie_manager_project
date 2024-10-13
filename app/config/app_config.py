# app_config.py
from app.config.base_config import BaseConfig


class AppConfig(BaseConfig):
    """应用程序主配置类。

    用于管理应用程序的一般配置，如数据库连接、API密钥等。

    示例:
        ```python
        config = AppConfig()
        database_url = config.get('database_url')
        api_key = config.get('api_key')
        ```
    """

    def __init__(self):
        """初始化应用配置，加载app.yml配置文件。"""
        super().__init__()
        self._load_config('app')

    def get_database_config(self):
        """返回数据库相关配置"""
        return self.config['database']

    def get_redis_config(self):
        """返回 Redis 缓存相关配置"""
        return self.config['redis']

    def get_jellyfin_config(self):
        """返回 Jellyfin 配置"""
        return self.config['jellyfin']

    def get_everything_config(self):
        """返回 everything 配置"""
        return self.config['everything']

    def get_qbittorrent_config(self):
        """返回 qbittorrent 配置"""
        return self.config['qbittorrent']

    def get_web_scraper_config(self):
        """返回爬虫配置"""
        return self.config['web_scraper']

    def get_md_file_path_config(self):
        """返回爬虫配置"""
        return self.config['md_file_path']
    def get_app_config(self):
        """返回应用程序配置"""
        return self.config['app']


# 以下为调用
from app.config.app_config import AppConfig


def main():
    config_loader = AppConfig()
    db_config = config_loader.get_database_config()
    jellyfin_config = config_loader.get_jellyfin_config()
    qbittorrent_config = config_loader.get_qbittorrent_config()

    print(db_config)
    print(jellyfin_config)
    print(qbittorrent_config)


if __name__ == "__main__":
    main()
