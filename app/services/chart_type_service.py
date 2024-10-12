from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Protocol
import re
import logging
from concurrent.futures import ThreadPoolExecutor
import threading

from app.config.config_app import AppConfig
from app.dao import ChartTypeDAO
from app.model.chart_file_type_enun import ChartFileType
from app.model.db.movie_model import Movie, ChartType
from app.model.md_file import md_file

# 配置日志记录器
from app.utils.read_markdown_file.markdown_reader import MarkdownReader
from app.utils.read_markdown_file.normal_markdown_reader import NormalMarkdownReader
from app.utils.read_markdown_file.top250_markdown_reader import Top250MarkdownReader

logger = logging.getLogger(__name__)

@dataclass
class ChartTypeService:
    """
    电影榜单分类服务类

    该服务类用于统一处理不同类型的电影榜单数据。

    Attributes:
        base_path: 基础文件路径
        readers: 不同类型榜单对应的读取器字典
    """
    base_path: Path
    readers: Dict[ChartFileType, MarkdownReader] = field(default_factory=dict)

    def __post_init__(self):
        """初始化服务，注册默认的读取器"""




    def __init__(self):

        self.config = AppConfig().get_md_file_path_config()

        self.chart_file_type = self.config.get('chart_file_type', ChartFileType.NORMAL)
        self.chart_type_name = self.config.get('chart_type_name', '')
        self.chart_type_description = self.config.get('chart_type_description', '')

        self.chart_type_dao = ChartTypeDAO()
        self.chart_type = ChartType(name=self.chart_type_name, description=self.chart_type_description, chart_file_type=self.chart_file_type)


    def get_by_name_or_create(self, chart_type: ChartType = None) -> Optional[ChartType]:
        """
        根据名称获取榜单类型，如果不存在则创建一个新的
        """
        if chart_type is None:
            chart_type = self.chart_type

        if not isinstance(chart_type, ChartType):
            raise ValueError("chart_type must be an instance of ChartType")

        try:
            flg = self.chart_type_dao.get_by_name(chart_type.name)
            if flg is None:
                return self.chart_type_dao.create(chart_type)
            else:
                return flg
        except Exception as e:
            # 处理异常
            print(f"An error occurred: {e}")
            return None