from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Tuple

from app.config.app_config import AppConfig
from app.dao import ChartDAO, MovieDAO
from app.model.chart_file_type_enun import ChartFileType
from app.model.db.movie_model import Movie, ChartType, Chart, ChartEntry
from app.model.enums import DownloadStatus
from app.model.mdfileinfo import MdFileInfo
from app.services.chart_entry_service import ChartEntryService
from app.services.chart_type_service import ChartTypeService
from app.services.movie_service import MovieService
from app.utils.log_util import debug, info, warning, error, critical
from app.utils.read_markdown_file.markdown_reader import MarkdownReader
from app.utils.read_markdown_file.normal_markdown_reader import NormalMarkdownReader
from app.utils.read_markdown_file.top250_markdown_reader import Top250MarkdownReader


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
        debug("ChartService post initialization completed")

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
        info("ChartService initialized")

    def get_base_path(self, base_path) -> Path:
        """获取基础路径"""
        if base_path is None:
            path = Path(Path(__file__).parent.parent.parent.parent / self.config['movie_list_path'])
        else:
            path = Path(Path(__file__).parent.parent.parent.parent / 'data/movies_list')
        debug(f"Base path set to: {path}")
        return path

    def get_movie_chart(self, chart_type: ChartType) -> List[MdFileInfo]:
        """
        获取指定类型的电影榜单

        Args:
            chart_type: 榜单类型

        Returns:
            List[MdFileInfo]: 包含电影信息的 md_file 列表

        Raises:
            ValueError: 当指定的榜单类型没有对应的读取器时抛出
        """
        reader = self.readers.get(chart_type)
        if not reader:
            error(f"不支持的榜单类型: {chart_type}")
            raise ValueError(f"不支持的榜单类型: {chart_type}")

        info(f"Reading movie chart for type: {chart_type}")
        return reader.read_files(self.base_path)

    def register_reader(self, chart_type: ChartType, reader: MarkdownReader):
        """注册新的榜单读取器"""
        self.readers[chart_type] = reader
        info(f"Registered new reader for chart type: {chart_type}")

    @staticmethod
    def get_movie_chart(chart_type: ChartType, path: str = "../data/movies_list") -> List[MdFileInfo]:
        """获取电影榜单的便捷函数"""
        service = ChartService(Path(path))
        info(f"Getting movie chart for type: {chart_type}")
        return service.get_movie_chart(chart_type)

    def get_movie_chart_and_chart_type(self, chart_type: ChartType = None) -> Tuple[List[MdFileInfo], ChartType]:
        """获取电影榜单数据及榜单类型"""
        chart_type_2 = self.chart_type_service.get_by_name_or_create(chart_type)
        reader = self.readers.get(self.chart_type_service.chart_file_type)
        if not reader:
            error(f"不支持的榜单类型: {self.chart_type_service.chart_file_type}")
            raise ValueError(f"不支持的榜单类型: {self.chart_type_service.chart_file_type}")

        info(f"Getting movie chart and chart type for: {chart_type}")
        return reader.read_files(), chart_type_2

    def save_chart_data_to_db_and_cache(self, md_file_list: List[MdFileInfo], chart_type: ChartType = None) -> bool:
        """保存榜单数据到数据库和缓存"""
        for md_file in md_file_list:
            chart = self.md_file_to_chart(md_file, chart_type_id=chart_type.id)
            chart_2 = self.chart_dao.get_by_name_or_create(chart)

            for movie_info in md_file.movie_info_list:
                movie_info.chart_id = chart_2.id
                movie = self.movie_dao.get_id_by_serial_number_or_create(movie=movie_info)
                chart_entry = self.movie_info_to_chart_entry(movie_info=movie, chart_id=chart_2.id,
                                                             rank=movie_info.rank)
                chart_entry_2 = self.chart_entry_service.get_chart_entry_by_movie_id_and_chart_id_or_create(chart_entry)
                info(f"插入成功: {movie_info.title}")

        info("Chart data saved to database and cache")
        return True

    def md_file_to_chart(self, md_file: MdFileInfo, chart_type_id: int = None) -> Chart:
        """将 MdFileInfo 转换为 Chart 对象"""
        debug(f"Converting MdFileInfo to Chart: {md_file.file_name}")
        return Chart(
            name=md_file.file_name.strip(".md"),
            description=md_file.description,
            chart_type_id=chart_type_id
        )

    def movie_info_to_chart_entry(self, movie_info: Movie, chart_id: int, rank: int) -> ChartEntry:
        """将 Movie 信息转换为 ChartEntry 对象"""
        debug(f"Converting Movie info to ChartEntry: {movie_info.title}")
        return ChartEntry(
            chart_id=chart_id,
            movie_id=movie_info.id,
            rank=rank,
            status=DownloadStatus.NOT_CRAWLED.value
        )

    def read_file_to_db(self):
        """读取 md 文件并将数据保存到数据库"""
        chart_type = self.chart_type_service.chart_type
        reader = self.readers.get(chart_type.chart_file_type)
        if not reader:
            error(f"不支持的榜单类型: {chart_type.chart_file_type}")
            raise ValueError(f"不支持的榜单类型: {chart_type.chart_file_type}")

        md_file_list = reader.read_files()
        info(f"Reading {len(md_file_list)} files to database")

        for md_file in md_file_list:
            chart = self.md_file_to_chart(md_file)
            for movie in md_file.movie_info_list:
                chart_entry = self.chart_entry_service.movie_to_chart_entry(movie=movie)
                chart_entry.movie = movie
                chart.entries.append(chart_entry)

            chart.chart_type = chart_type
            flg = self.chart_dao.create(chart)
            info(f"Chart created: {flg}")

    def create(self, chart: Chart):
        return self.chart_dao.create(chart)

    def get_reader(self, chart_file_type: str ):
        reader = self.readers.get(chart_file_type)
        if not reader:
            error(f"不支持的榜单类型: {chart_file_type}")
            raise ValueError(f"不支持的榜单类型: {chart_file_type}")
        return reader