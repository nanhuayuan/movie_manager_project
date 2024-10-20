import logging
import logging.config
import os
from pathlib import Path
import yaml
from typing import Dict, Any

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

    @classmethod
    def get_project_root(cls) -> Path:
        """获取项目根目录"""
        return Path(__file__).parent.parent.parent

    @classmethod
    def get_log_dir(cls) -> Path:
        """从配置中获取日志目录路径"""
        config = LogConfig()
        log_dir_name = config.get('log_directory', 'logs')
        return cls.get_project_root() / log_dir_name

    def _load_base_config(self) -> Dict[str, Any]:
        """加载基础配置文件"""
        config_dir = self.get_project_root() / 'config'
        base_config_file = config_dir / 'logging-base.yml'

        try:
            with base_config_file.open(encoding='utf-8') as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            print(f"Warning: Could not load base config: {e}")
            return {}

    def _merge_configs(self, base_config: Dict[str, Any], env_config: Dict[str, Any]) -> Dict[str, Any]:
        """合并基础配置和环境配置"""
        merged = base_config.copy()

        def deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> None:
            for key, value in override.items():
                if (
                        key in base
                        and isinstance(base[key], dict)
                        and isinstance(value, dict)
                ):
                    deep_merge(base[key], value)
                else:
                    base[key] = value

        if env_config:
            deep_merge(merged, env_config)

        # 确保root logger配置存在
        if 'loggers' not in merged:
            merged['loggers'] = {}
        if '' not in merged['loggers']:
            merged['loggers'][''] = {
                'level': 'INFO',
                'handlers': ['console', 'file', 'error_file'],
                'propagate': True
            }

        return merged

    def _process_file_handlers(self, config: Dict[str, Any]) -> None:
        """处理文件处理器的路径和权限"""
        log_dir = self.get_log_dir()
        log_dir.mkdir(parents=True, exist_ok=True)

        for handler_name, handler_config in config.get('handlers', {}).items():
            if 'filename' in handler_config:
                if os.path.isabs(handler_config['filename']):
                    log_path = Path(handler_config['filename'])
                else:
                    log_path = log_dir / handler_config['filename']

                log_path.parent.mkdir(parents=True, exist_ok=True)
                handler_config['filename'] = str(log_path)

                if os.getenv('APP_ENV') == 'prod' and 'mode' in handler_config:
                    if log_path.exists():
                        os.chmod(str(log_path), int(handler_config['mode'], 8))

    def _ensure_console_handler(self, config: Dict[str, Any]) -> None:
        """确保console handler存在且配置正确"""
        if 'handlers' not in config:
            config['handlers'] = {}

        if 'console' not in config['handlers']:
            config['handlers']['console'] = {
                'class': 'logging.StreamHandler',
                'level': 'DEBUG' if os.getenv('APP_ENV') == 'dev' else 'INFO',
                'formatter': 'simple',
                'stream': 'ext://sys.stdout'
            }

    def _setup_logging(self):
        """设置日志系统"""
        try:
            # 加载并合并配置
            base_config = self._load_base_config()
            env_config = self._config.config
            logging_config = self._merge_configs(base_config, env_config)

            # 确保必要的配置存在
            self._ensure_console_handler(logging_config)
            self._process_file_handlers(logging_config)

            # 测试环境特殊处理
            if os.getenv('TESTING') == 'true':
                self._configure_test_environment(logging_config)

            # 应用配置
            logging.config.dictConfig(logging_config)

        except Exception as e:
            print(f"Error setting up logging configuration: {str(e)}")
            self._setup_fallback_logging()

    def _configure_test_environment(self, config: Dict[str, Any]) -> None:
        """配置测试环境特定设置"""
        self._ensure_console_handler(config)
        config['handlers']['console']['level'] = 'DEBUG'

        # 确保root logger配置正确
        if '' not in config['loggers']:
            config['loggers'][''] = {}

        root_logger_config = config['loggers']['']
        root_logger_config['level'] = 'DEBUG'
        root_logger_config['handlers'] = root_logger_config.get('handlers', [])
        if 'console' not in root_logger_config['handlers']:
            root_logger_config['handlers'].append('console')

    def _setup_fallback_logging(self):
        """设置基本的后备日志配置"""
        logging.basicConfig(
            level=logging.DEBUG if os.getenv('TESTING') == 'true' else logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S',
            force=True
        )

    @staticmethod
    def get_logger(name=None):
        """获取logger实例，确保总是有控制台输出"""
        logger = logging.getLogger(name)

        # 检查logger及其所有父级是否有任何handlers
        def has_handlers(log):
            while log:
                if log.handlers:
                    return True
                log = log.parent
            return False

        # 如果没有任何handlers，添加一个基本的控制台handler
        if not has_handlers(logger):
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(
                logging.Formatter(
                    '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    '%Y-%m-%d %H:%M:%S'
                )
            )
            logger.addHandler(console_handler)

            # 确保级别设置正确
            logger.setLevel(
                logging.DEBUG
                if os.getenv('APP_ENV') == 'dev' or os.getenv('TESTING') == 'true'
                else logging.INFO
            )

        return logger


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