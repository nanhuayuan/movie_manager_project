# log_config.py
import logging
import logging.config
import os
from pathlib import Path
from typing import Any, Dict

import yaml

from app.config.base_config import BaseConfig


class LogConfig(BaseConfig):
    def __init__(self):
        super().__init__()
        self._load_config('logging')


class LogUtil:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(LogUtil, cls).__new__(cls)
            cls._instance._config = LogConfig()
            cls._instance._setup_logging()
        return cls._instance

    def _setup_logging(self):
        # 直接使用 LogConfig 中已经合并好的配置
        logging_config = self._config.config
        self._process_log_paths(logging_config)

        # 添加调试日志(可选)
        print("Loaded logging config:", logging_config)

        # 验证配置完整性
        self._validate_logging_config(logging_config)
        logging.config.dictConfig(logging_config)

    def _validate_logging_config(self, config: Dict[str, Any]) -> None:
        """验证日志配置的完整性"""
        required_handler_keys = {
            'console': ['class', 'formatter', 'level'],
            'file': ['class', 'formatter', 'level', 'filename'],
            'error_file': ['class', 'formatter', 'level', 'filename']
        }

        for handler_name, required_keys in required_handler_keys.items():
            handler_config = config.get('handlers', {}).get(handler_name, {})
            missing_keys = [key for key in required_keys if key not in handler_config]
            if missing_keys:
                raise ValueError(f"Handler '{handler_name}' missing required keys: {missing_keys}")

    def _process_log_paths(self, config: Dict[str, Any]):
        log_dir = Path(config.get('log_directory', 'logs'))
        log_dir.mkdir(parents=True, exist_ok=True)

        for handler in config.get('handlers', {}).values():
            if 'filename' in handler:
                log_path = log_dir / handler['filename']
                handler['filename'] = str(log_path)

    @staticmethod
    def get_logger(name=None):
        return logging.getLogger(name)


logger = LogUtil().get_logger()


def debug(msg, *args, **kwargs): logger.debug(msg, *args, **kwargs)


def info(msg, *args, **kwargs): logger.info(msg, *args, **kwargs)


def warning(msg, *args, **kwargs): logger.warning(msg, *args, **kwargs)


def error(msg, *args, **kwargs): logger.error(msg, *args, **kwargs)


def critical(msg, *args, **kwargs): logger.critical(msg, *args, **kwargs)