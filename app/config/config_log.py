# utils/config_log.py

# config_log.py
from app.config.base_config import BaseConfig
from typing import Any, Dict


class LogConfig(BaseConfig):
    """日志配置管理类。

    专门用于管理日志相关的配置，如日志级别、格式、输出位置等。

    示例:
        ```python
        log_config = LogConfig()
        log_level = log_config.get('level', 'INFO')
        log_format = log_config.get('format')
        ```
    """

    def __init__(self):
        """初始化日志配置，加载logging.yml配置文件。"""
        super().__init__()
        self._load_config('logging')

    def get_file_handler_config(self) -> Dict[str, Any]:
        """获取文件处理器的配置。

        Returns:
            Dict[str, Any]: 文件处理器的配置字典
        """
        return self.get('file_handler', {})

    def get_console_handler_config(self) -> Dict[str, Any]:
        """获取控制台处理器的配置。

        Returns:
            Dict[str, Any]: 控制台处理器的配置字典
        """
        return self.get('console_handler', {})

    def get_db_log_config(self) -> dict:
        """获取数据库日志配置"""
        return self.get('handlers', {}).get('database', {})
