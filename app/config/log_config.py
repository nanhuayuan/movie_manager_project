# log_config.py
import logging
import logging.config
import os
import sys
from pathlib import Path
from typing import Any, Dict

import yaml

from app.config.base_config import BaseConfig


class LogConfig(BaseConfig):
    """日志配置类，负责加载和管理日志配置"""

    def __init__(self):
        super().__init__()
        self._load_config('logging')


class ImmediateFormatter(logging.Formatter):
    """
    实时输出的日志格式化器
    确保每条日志立即刷新输出
    """

    def __init__(self, fmt=None, datefmt=None):
        super().__init__(fmt, datefmt)

    def format(self, record):
        formatted_message = super().format(record)
        # 确保每条日志后都刷新输出
        sys.stdout.flush()
        sys.stderr.flush()
        return formatted_message


class ImmediateStreamHandler(logging.StreamHandler):
    """
    立即输出的流处理器
    重写emit方法确保实时输出
    """

    def emit(self, record):
        try:
            msg = self.format(record)
            stream = self.stream
            # 写入消息并立即刷新
            stream.write(msg + self.terminator)
            stream.flush()
        except Exception:
            self.handleError(record)


class LogUtil:
    """
    日志工具类，实现单例模式
    负责初始化日志系统，提供日志记录接口
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(LogUtil, cls).__new__(cls)
            cls._instance._config = LogConfig()
            cls._instance._setup_logging()
        return cls._instance

    def _setup_logging(self):
        """
        设置日志系统，包括:
        1. 处理日志路径
        2. 配置控制台实时输出
        3. 验证配置完整性
        """
        # 先注册自定义的Formatter
        logging.setLoggerClass(logging.Logger)
        logging.setLogRecordFactory(logging.LogRecord)

        logging_config = self._config.config
        self._process_log_paths(logging_config)
        self._configure_immediate_console_output(logging_config)

        self._validate_logging_config(logging_config)
        logging.config.dictConfig(logging_config)

    def _configure_immediate_console_output(self, config: Dict[str, Any]):
        """
        配置控制台处理器实现实时输出
        使用简单的配置确保实时显示
        """
        # 确保formatters部分存在
        if 'formatters' not in config:
            config['formatters'] = {}

        # 使用标准的formatter配置
        config['formatters']['console'] = {
            'format': '%(asctime)s - %(levelname)s - [%(name)s] - %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S'
        }

        # 配置console handler
        console_handler = config.get('handlers', {}).get('console', {})
        if console_handler:
            console_handler.update({
                'class': 'logging.StreamHandler',
                'formatter': 'console',
                'stream': 'ext://sys.stderr',  # 使用stderr
                'level': 'DEBUG'  # 确保能看到所有级别的日志
            })

        # 确保root logger的级别设置正确
        if 'root' not in config:
            config['root'] = {}
        config['root']['level'] = 'DEBUG'

    def _validate_logging_config(self, config: Dict[str, Any]) -> None:
        """
        验证日志配置的完整性
        检查所有必需的配置项是否存在
        """
        required_handler_keys = {
            'console': ['class', 'formatter', 'level'],
            'file': ['class', 'formatter', 'level', 'filename'],
            'error_file': ['class', 'formatter', 'level', 'filename']
        }

        for handler_name, required_keys in required_handler_keys.items():
            handler_config = config.get('handlers', {}).get(handler_name, {})
            missing_keys = [key for key in required_keys if key not in handler_config]
            if missing_keys:
                raise ValueError(f"处理器 '{handler_name}' 缺少必需的配置项: {missing_keys}")

    def _process_log_paths(self, config: Dict[str, Any]):
        """
        处理日志文件路径:
        1. 优先使用配置文件中指定的日志目录
        2. 如果是相对路径，则相对于项目根目录
        3. 如果未指定，则使用项目根目录下的默认logs目录
        """
        # 获取项目根目录（查找到包含 config 目录的父目录）
        current_dir = Path(__file__).resolve()
        project_root = None
        for parent in current_dir.parents:
            if (parent / 'config').exists():
                project_root = parent
                break

        if not project_root:
            raise ValueError("无法找到项目根目录")

        # 获取配置中的日志目录，如果没有配置则使用默认值
        log_directory = config.get('log_directory', 'logs')

        # 处理日志目录路径
        log_dir = Path(log_directory)
        if not log_dir.is_absolute():
            # 如果是相对路径，则相对于项目根目录
            log_dir = project_root / log_directory

        # 确保日志目录存在
        log_dir.mkdir(parents=True, exist_ok=True)

        # 更新配置中的日志目录为绝对路径
        config['log_directory'] = str(log_dir)

        # 处理所有处理器的文件路径
        for handler_name, handler in config.get('handlers', {}).items():
            if 'filename' in handler:
                # 如果处理器的文件名是相对路径，则相对于日志目录
                filename = Path(handler['filename'])
                if not filename.is_absolute():
                    log_path = log_dir / filename
                else:
                    log_path = filename
                handler['filename'] = str(log_path)

    @staticmethod
    def get_logger(name=None):
        """获取logger实例"""
        logger = logging.getLogger(name)
        return logger


# 创建全局日志工具实例
logger = LogUtil().get_logger()


# 提供便捷的日志记录函数
def debug(msg, *args, **kwargs):
    """记录debug级别日志"""
    logger.debug(msg, *args, **kwargs)


def info(msg, *args, **kwargs):
    """记录info级别日志"""
    logger.info(msg, *args, **kwargs)


def warning(msg, *args, **kwargs):
    """记录warning级别日志"""
    logger.warning(msg, *args, **kwargs)


def error(msg, *args, **kwargs):
    """记录error级别日志"""
    logger.error(msg, *args, **kwargs)


def critical(msg, *args, **kwargs):
    """记录critical级别日志"""
    logger.critical(msg, *args, **kwargs)