# log_config.py
import logging
import logging.config
import os
from pathlib import Path
from plistlib import Dict
from typing import Any

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
        config_dir = Path(__file__).parent.parent.parent / 'config'
        base_config = self._read_yaml(config_dir / 'logging-base.yml')
        env = os.getenv('APP_ENV', 'dev')
        env_config = self._read_yaml(config_dir / f'logging-{env}.yml')

        logging_config = base_config.copy()
        logging_config.update(env_config)

        self._process_log_paths(logging_config)
        logging.config.dictConfig(logging_config)

    def _process_log_paths(self, config: Dict[str, Any]):
        log_dir = Path(config.get('log_directory', 'logs'))
        log_dir.mkdir(parents=True, exist_ok=True)

        for handler in config.get('handlers', {}).values():
            if 'filename' in handler:
                log_path = log_dir / handler['filename']
                handler['filename'] = str(log_path)

    @staticmethod
    def _read_yaml(file_path: Path) -> Dict[str, Any]:
        with file_path.open(encoding='utf-8') as f:
            return yaml.safe_load(f) or {}

    @staticmethod
    def get_logger(name=None):
        return logging.getLogger(name)


logger = LogUtil().get_logger()


def debug(msg, *args, **kwargs): logger.debug(msg, *args, **kwargs)


def info(msg, *args, **kwargs): logger.info(msg, *args, **kwargs)


def warning(msg, *args, **kwargs): logger.warning(msg, *args, **kwargs)


def error(msg, *args, **kwargs): logger.error(msg, *args, **kwargs)


def critical(msg, *args, **kwargs): logger.critical(msg, *args, **kwargs)