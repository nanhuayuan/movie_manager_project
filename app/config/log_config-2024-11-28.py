# app/config/log_config.py
import logging
import logging.config
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
import yaml

from app.config.base_config import BaseConfig




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


class LogUtil:
    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(LogUtil, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._initialized:
            import logging
            import logging.config

            # 读取配置文件并转换为UTF-8编码
            logging.config.fileConfig('D:\project\movie_manager_project\config\logging.conf')

            LogUtil._initialized = True



    @staticmethod
    def get_logger(name='fileAndConsole'):
        """获取logger实例"""
        return logging.getLogger(name)

# 创建全局日志实例
my_logger = LogUtil().get_logger('fileAndConsole')

# 便捷的日志记录函数
def debug(msg, *args, **kwargs):
    my_logger.debug(msg, *args, **kwargs)


def info(msg, *args, **kwargs):
    my_logger.info(msg, *args, **kwargs)


def warning(msg, *args, **kwargs):
    my_logger.warning(msg, *args, **kwargs)


def error(msg, *args, **kwargs):
    my_logger.error(msg, *args, **kwargs)


def critical(msg, *args, **kwargs):
    logger.critical(msg, *args, **kwargs)