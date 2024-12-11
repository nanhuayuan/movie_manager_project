# app/config/log_config.py
import logging
import logging.config
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.config.base_config import BaseConfig


class ImmediateStreamHandler(logging.StreamHandler):
    """确保立即刷新的流处理器"""

    def __init__(self, stream=None):
        # 如果没有指定stream，默认使用stdout
        if stream is None:
            stream = sys.stdout
        super().__init__(stream)

        # 设置stream为无缓冲模式
        if hasattr(stream, 'reconfigure'):  # Python 3.7+
            stream.reconfigure(line_buffering=True)
        else:
            # 对于较老的Python版本
            import io
            if isinstance(stream, io.TextIOBase):
                stream.flush()
                stream = io.TextIOWrapper(
                    stream.buffer,
                    stream.encoding,
                    line_buffering=True
                )
        self.stream = stream

    def emit(self, record):
        """确保每条日志立即输出"""
        try:
            msg = self.format(record)
            stream = self.stream
            stream.write(msg + self.terminator)
            self.flush()  # 立即刷新缓冲区
        except Exception:
            self.handleError(record)

    def flush(self):
        """确保刷新处理"""
        if self.stream and hasattr(self.stream, "flush"):
            self.stream.flush()


class ProjectPathFinder:
    """项目路径查找器"""

    # 项目根目录标志文件/目录列表
    PROJECT_MARKERS: List[str] = [
        'pyproject.toml',  # Poetry 项目文件
        'setup.py',  # 传统的 setup.py
        '.git',  # Git 仓库
        'requirements.txt',  # 依赖文件
        #'config',  # 配置目录
        'README.md'  # README 文件
    ]

    @classmethod
    def find_project_root(cls, start_path: Optional[Path] = None) -> Path:
        """
        查找项目根目录

        Args:
            start_path: 开始搜索的路径，默认为当前文件所在目录

        Returns:
            Path: 项目根目录的路径

        Raises:
            ValueError: 如果找不到项目根目录
        """
        if start_path is None:
            start_path = Path(__file__).resolve().parent

        current_path = start_path

        # 向上查找，直到找到项目根目录或到达根目录
        while True:
            # 检查当前目录是否包含项目标志
            for marker in cls.PROJECT_MARKERS:
                if (current_path / marker).exists():
                    return current_path

            # 如果到达根目录仍未找到，则使用工作目录
            if current_path.parent == current_path:
                # 如果找不到任何标志，使用当前工作目录
                working_dir = Path.cwd()
                print(f"警告: 未找到项目根目录标志，使用当前工作目录: {working_dir}")
                return working_dir

            # 移动到父目录继续查找
            current_path = current_path.parent


class LogConfig(BaseConfig):
    """日志配置类"""

    def __init__(self):
        super().__init__()
        self._load_config('logging')

    def get_log_directory(self) -> Path:
        """获取配置的日志目录"""
        return Path(self.config.get('log_directory', 'logs'))


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
            LogUtil._initialized = True

    def _setup_logging(self):
        """设置日志系统"""
        # 注册自定义Handler
        #if not hasattr(logging, 'ImmediateStreamHandler'):
        #    logging.ImmediateStreamHandler = ImmediateStreamHandler

        config = self._config.config.copy()

        # 找到项目根目录并设置日志目录
        project_root = ProjectPathFinder.find_project_root()
        log_dir = project_root / self._config.get_log_directory()

        # 确保日志目录存在
        log_dir.mkdir(parents=True, exist_ok=True)

        # 更新所有handler的文件路径
        handlers = config.get('handlers', {})
        for handler_name, handler_config in handlers.items():
            if 'filename' in handler_config:
                filename = Path(handler_config['filename'])
                if not filename.is_absolute():
                    abs_path = log_dir / filename
                    handler_config['filename'] = str(abs_path)
                    print(f"Handler {handler_name} 的日志文件路径: {abs_path}")

        # 配置控制台输出
        #self._configure_console_handler(config)

        try:
            logging.config.dictConfig(config)
        except ValueError as e:
            print(f"日志配置错误: {e}", file=sys.stderr)
            raise

    def _configure_console_handler(self, config: Dict[str, Any]):
        """配置控制台处理器"""
        # 确保基本配置存在
        if 'formatters' not in config:
            config['formatters'] = {}
        if 'handlers' not in config:
            config['handlers'] = {}
        if 'loggers' not in config:
            config['loggers'] = {}

        # 配置控制台格式化器
        config['formatters']['console'] = {
            'format': '%(asctime)s - %(levelname)s - [%(name)s] - %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S'
        }

        # 配置控制台处理器
        config['handlers']['console'] = {
            'class': 'logging.ImmediateStreamHandler',
            'level': 'DEBUG',  # 默认使用DEBUG级别以显示所有日志
            'formatter': 'console',
            'stream': 'ext://sys.stdout'
        }

        # 确保root logger使用控制台处理器
        if 'root' not in config:
            config['root'] = {}

        handlers = config['root'].get('handlers', [])
        if 'console' not in handlers:
            handlers.append('console')
            config['root']['handlers'] = handlers

        # 设置基本配置
        config['version'] = 1
        config['disable_existing_loggers'] = False

    @staticmethod
    def get_logger(name=None):
        """获取logger实例"""
        return logging.getLogger(name)


# 创建全局日志实例
logger = LogUtil().get_logger('fileAndConsole')


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