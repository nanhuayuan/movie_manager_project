import logging
import logging.config
from pathlib import Path

from app.config.log_config import LogConfig

class LogUtil:
    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(LogUtil, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._initialized:
            self._config = LogConfig()
            self._setup_logging()
            self._initialized = True

    def _validate_handler_config(self, handler_config):
        required_keys = ['class', 'level', 'formatter']
        for key in required_keys:
            if key not in handler_config:
                raise ValueError(f"Missing required key '{key}' in handler config")

    def _setup_logging(self):
        try:
            # 确保日志目录存在
            log_dir = Path(self._config.get('handlers', {}).get('file', {}).get('filename', 'logs/app.log')).parent
            log_dir.mkdir(parents=True, exist_ok=True)

            logging_config = {
                'version': 1,
                'disable_existing_loggers': False,
                'formatters': {
                    'simple': self._config.get_formatter_config('simple'),
                    'database': self._config.get_formatter_config('database'),
                },
                'handlers': {
                    'console': self._config.get_handler_config('console'),
                    'file': self._config.get_handler_config('file'),
                    'database': self._config.get_handler_config('database'),
                },
                'loggers': {
                    '': self._config.get_logger_config('root'),
                    'sqlalchemy': self._config.get_logger_config('sqlalchemy'),
                }
            }

            # Validate handler configurations
            for handler_name, handler_config in logging_config['handlers'].items():
                self._validate_handler_config(handler_config)

            # 设置数据库日志的控制台输出级别
            db_console_level = self._config.get_database_log_config().get('console_output', 'DEBUG')
            if 'console' in logging_config['handlers']:
                logging_config['handlers']['console']['level'] = db_console_level

            logging.config.dictConfig(logging_config)
        except Exception as e:
            print(f"Error setting up logging configuration: {str(e)}")
            print("Falling back to basic logging configuration")
            logging.basicConfig(level=logging.INFO)

    @staticmethod
    def get_logger(name=None):
        return logging.getLogger(name)

# 全局logger实例
logger = LogUtil().get_logger()

# 便捷的日志记录方法
def debug(msg, *args, **kwargs):
    logger.debug(msg, *args, **kwargs)

def info(msg, *args, **kwargs):
    logger.info(msg, *args, **kwargs)

def warning(msg, *args, **kwargs):
    logger.warning(msg, *args, **kwargs)

def error(msg, *args, **kwargs):
    logger.error(msg, *args, **kwargs)

def critical(msg, *args, **kwargs):
    logger.critical(msg, *args, **kwargs)