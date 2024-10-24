# log_config.py
import logging
import logging.config
import os
import sys
from pathlib import Path
from typing import Any, Dict

import yaml
from app.config.base_config import BaseConfig


class ImmediateStreamHandler(logging.StreamHandler):
    """确保立即刷新的流处理器"""

    def __init__(self):
        super().__init__(sys.stdout)
        # 设置stream为无缓冲模式
        try:
            self.stream.reconfigure(line_buffering=True)  # Python 3.7+
        except AttributeError:
            self.stream = os.fdopen(self.stream.fileno(), 'w', 1)

    def emit(self, record):
        """重写emit确保立即输出"""
        try:
            msg = self.format(record)
            self.stream.write(msg + self.terminator)
            self.stream.flush()  # 立即刷新缓冲区
        except Exception:
            self.handleError(record)


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
        """设置日志系统"""
        # 确保在配置前注册自定义的Handler类
        logging.ImmediateStreamHandler = ImmediateStreamHandler

        logging_config = self._config.config
        self._process_log_paths(logging_config)
        self._configure_immediate_console_output(logging_config)

        try:
            logging.config.dictConfig(logging_config)
        except ValueError as e:
            print(f"日志配置错误: {e}")
            raise

    def _configure_immediate_console_output(self, config: Dict[str, Any]):
        """配置控制台实时输出"""
        # 配置formatter
        if 'formatters' not in config:
            config['formatters'] = {}

        config['formatters']['console'] = {
            'format': '%(asctime)s - %(levelname)s - [%(name)s] - %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S'
        }

        # 配置实时输出的console handler
        if 'handlers' not in config:
            config['handlers'] = {}

        config['handlers']['console'] = {
            'class': 'logging.ImmediateStreamHandler',  # 修改这里，使用注册后的类名
            'level': 'DEBUG',
            'formatter': 'console'
        }

        # 确保root logger配置正确
        if 'root' not in config:
            config['root'] = {}

        config['root'].update({
            'level': 'DEBUG',
            'handlers': ['console']
        })

        # 确保version字段存在
        config['version'] = 1
        config['disable_existing_loggers'] = False

    def _process_log_paths(self, config: Dict[str, Any]):
        """处理日志文件路径"""
        # 获取项目根目录
        current_dir = Path(__file__).resolve()
        project_root = None
        for parent in current_dir.parents:
            if (parent / 'config').exists():
                project_root = parent
                break

        if not project_root:
            raise ValueError("无法找到项目根目录")

        # 获取日志目录
        log_directory = config.get('log_directory', 'logs')
        log_dir = Path(log_directory)

        if not log_dir.is_absolute():
            log_dir = project_root / log_directory

        # 确保日志目录存在
        log_dir.mkdir(parents=True, exist_ok=True)

        # 更新配置中的日志路径
        config['log_directory'] = str(log_dir)

        # 处理所有处理器的文件路径
        for handler_name, handler in config.get('handlers', {}).items():
            if 'filename' in handler:
                filename = Path(handler['filename'])
                if not filename.is_absolute():
                    log_path = log_dir / filename
                else:
                    log_path = filename
                handler['filename'] = str(log_path)

    @staticmethod
    def get_logger(name=None):
        """获取logger实例"""
        return logging.getLogger(name)


# 创建全局日志实例
logger = LogUtil().get_logger()


# 便捷的日志记录函数
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