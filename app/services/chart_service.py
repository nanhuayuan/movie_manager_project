from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Protocol, Tuple
import re
import logging
from concurrent.futures import ThreadPoolExecutor
import threading

from app.config.app_config import AppConfig
from app.dao import ChartDAO, MovieDAO
from app.model.chart_file_type_enun import ChartFileType
from app.model.db.movie_model import Movie, ChartType, Chart, ChartEntry
from app.model.enums import DownloadStatus
from app.model.md_file import md_file

# 配置日志记录器
from app.services.chart_type_service import ChartTypeService
from app.services.movie_service import MovieService
from app.services.chart_entry_service import  ChartEntryService
from app.utils.db_util import db
from app.utils.read_markdown_file.markdown_reader import MarkdownReader
from app.utils.read_markdown_file.normal_markdown_reader import NormalMarkdownReader
from app.utils.read_markdown_file.top250_markdown_reader import Top250MarkdownReader

logger = logging.getLogger(__name__)


@dataclass
class ChartService:
    """
    电影榜单服务类

    该服务类用于统一处理不同类型的电影榜单数据。

    Attributes:
        base_path: 基础文件路径
        readers: 不同类型榜单对应的读取器字典
    """
    base_path: Path
    readers: Dict[ChartFileType, MarkdownReader] = field(default_factory=dict)

    def __post_init__(self):
        """初始化服务，注册默认的读取器"""
        self.base_path = Path(self.base_path)


    def __init__(self):

        self.readers = {
            ChartFileType.NORMAL.value: NormalMarkdownReader(),
            ChartFileType.TOP_250.value: Top250MarkdownReader()
        }
        self.config = AppConfig().get_md_file_path_config()

        self.base_path = self.get_base_path(self.config['movie_list_path'])

        self.chart_file_type = self.config.get('chart_file_type', ChartFileType.NORMAL)
        self.chart_type_name = self.config.get('chart_type_name', '')
        self.chart_type_description = self.config.get('chart_type_description', '')

        self.chart_type = ChartType(name=self.chart_type_name, description=self.chart_type_description)

        self.movie_service = MovieService()
        self.chart_type_service = ChartTypeService()
        self.chart_entry_service = ChartEntryService()
        self.chart_dao = ChartDAO()
        self.movie_dao = MovieDAO()


    def get_base_path(self, base_path) -> List[md_file]:

        if base_path is None:
            return Path(Path(__file__).parent.parent.parent.parent / self.config['movie_list_path'])

        return Path(Path(__file__).parent.parent.parent.parent / 'data/movies_list')

    def get_movie_chart(self, chart_type: ChartType) -> List[md_file]:
        """
        获取指定类型的电影榜单

        Args:
            chart_type: 榜单类型

        Returns:
            List[md_file]: 包含电影信息的 md_file 列表

        Raises:
            ValueError: 当指定的榜单类型没有对应的读取器时抛出
        """
        reader = self.readers.get(chart_type)
        if not reader:
            raise ValueError(f"不支持的榜单类型: {chart_type}")

        return reader.read_files(self.base_path)

    def register_reader(self, chart_type: ChartType, reader: MarkdownReader):
        """
        注册新的榜单读取器

        Args:
            chart_type: 榜单类型
            reader: 对应的读取器实现
        """
        self.readers[chart_type] = reader

    def get_movie_chart(chart_type: ChartType,
                        path: str = "../data/movies_list") -> List[md_file]:
        """
        获取电影榜单的便捷函数

        Args:
            chart_type: 榜单类型
            path: 文件目录路径

        Returns:
            List[md_file]: 包含电影信息的 md_file 列表

        Examples:
            >>> top_250_movies = get_movie_chart(ChartType.TOP_250)
            >>> normal_movies = get_movie_chart(ChartType.NORMAL)
        """
        service = ChartService(Path(path))
        return service.get_movie_chart(chart_type)

    def get_movie_chart_and_chary_type(self, chart_type: ChartType = None) -> Tuple[List[md_file],ChartType]:
        """
           获取电影图表数据及图表类型。

           :param chart_type: 图表类型，默认为折线图
           :return: 包含图表数据的列表和图表类型
           """
        chart_type_2 = self.chart_type_service.get_by_name_or_create(chart_type)

        reader = self.readers.get(self.chart_type_service.chart_file_type)
        if not reader:
            raise ValueError(f"不支持的榜单类型: {self.chart_type_service.chart_file_type}")

        return reader.read_files(),chart_type_2

    def save_chart_data_to_db_and_cache(self, md_file_list: List[md_file], chart_type: ChartType = None) -> bool:

        # 列表，循环判断每一个榜单文件，如果存在，则更新，不存在，则插入
        for md_file in md_file_list:
            chart = self.md_file_to_chart(md_file,chart_type_id=chart_type.id)

            chart_2 = self.chart_dao.get_by_name_or_create(chart)
            # 插入电影信息和榜单
            for movie_info in md_file.movie_info_list:
                movie_info.chart_id = chart_2.id

                movie = self.movie_dao.get_id_by_serial_number_or_create(movie=movie_info)

                chart_entry = self.movie_info_to_chart_entry(movie_info=movie,chart_id = chart_2.id,rank = movie_info.ranking)

                chart_entry_2 = self.chart_entry_service.get_by_movie_id_or_create(chart_entry)


        return True

    def md_file_to_chart(self, md_file: md_file,chart_type_id: int) -> Chart:

        return Chart(
            name = md_file.file_name.strip(".md"),
            description = md_file.description,
            chart_type_id= chart_type_id
            )

    def movie_info_to_chart_entry(self, movie_info: Movie,chart_id: int,rank: int) -> ChartEntry:

        return ChartEntry(
            chart_id = chart_id,
            movie_id = movie_info.id,
            rank = rank,
            #score = movie_info.score,
            #votes = ,
            status = DownloadStatus.NOT_CRAWLED.value
            )

