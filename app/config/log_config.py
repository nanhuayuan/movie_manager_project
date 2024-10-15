from app.config.base_config import BaseConfig
from typing import Any, Dict

class LogConfig(BaseConfig):
    """日志配置管理类。"""

    def __init__(self):
        """初始化日志配置，加载logging.yml配置文件。"""
        super().__init__()
        self._load_config('logging')

    def get_handler_config(self, handler_name: str) -> Dict[str, Any]:
        """获取指定处理器的配置。"""
        return self.get('handlers', {}).get(handler_name, {})

    def get_formatter_config(self, formatter_name: str) -> Dict[str, Any]:
        """获取指定格式化器的配置。"""
        return self.get('formatters', {}).get(formatter_name, {})

    def get_logger_config(self, logger_name: str = 'root') -> Dict[str, Any]:
        """获取指定日志记录器的配置。"""
        return self.get('loggers', {}).get(logger_name, {})

    def get_database_log_config(self) -> Dict[str, Any]:
        """获取数据库日志的额外配置。"""
        return self.get('database_log', {})