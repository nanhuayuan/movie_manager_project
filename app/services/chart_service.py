from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Tuple, Optional

from app.config.app_config import AppConfig
from app.dao import ChartDAO, MovieDAO
from app.model.chart_file_type_enun import ChartFileType
from app.model.db.movie_model import Movie, ChartType, Chart, ChartEntry
from app.model.enums import DownloadStatus
from app.model.mdfileinfo import MdFileInfo
from app.services.base_service import BaseService
from app.services.chart_entry_service import ChartEntryService
from app.services.chart_type_service import ChartTypeService
from app.config.log_config import debug, info, warning, error, critical
from app.utils.read_markdown_file.markdown_reader import MarkdownReader
from app.utils.read_markdown_file.normal_markdown_reader import NormalMarkdownReader
from app.utils.read_markdown_file.top250_markdown_reader import Top250MarkdownReader


@dataclass
class ChartService(BaseService[Chart, ChartDAO]):
    """
    电影榜单服务类

    该服务类用于统一处理不同类型的电影榜单数据。

    Attributes:
        chart_list_path: 基础文件路径
        readers: 不同类型榜单对应的读取器字典
    """
    chart_list_path: Path
    readers: Dict[ChartFileType, MarkdownReader] = field(default_factory=dict)

    def __post_init__(self):
        """初始化服务，注册默认的读取器"""
        # self.chart_list_path = Path(self.chart_list_path)
        debug("ChartService post initialization completed")

    def __init__(self):
        super().__init__()

        self.readers = {
            ChartFileType.NORMAL.value: NormalMarkdownReader(),
            ChartFileType.TOP_250.value: Top250MarkdownReader()
        }
        self.config = AppConfig().get_chart_config()
        self.chart_list_path = self.get_chart_list_path(self.config['chart_list_path'])
        self.markdown_reader_name = self.config.get('markdown_reader', ChartFileType.NORMAL.value)

        self.chart_type_service = ChartTypeService()
        self.chart_entry_service = ChartEntryService()
        self.chart_dao = ChartDAO()
        self.movie_dao = MovieDAO()
        info("ChartService initialized")

    def get_chart_list_path(self, chart_list_path) -> Path:
        """获取基础路径"""
        if chart_list_path is None:
            path = Path(Path(__file__).parent.parent.parent.parent / self.config['chart_list_path'])
        else:
            path = Path(Path(__file__).parent.parent.parent.parent / 'data/chart_list')
        debug(f"Base path set to: {path}")
        return path

    def get_default_markdown_reader_name(self) -> str:
        return self.markdown_reader_name

    def get_by_name_or_create(self, chart: Chart = None) -> Optional[Chart]:

        debug(f"Entering get_by_name_or_create with chart: {chart}")

        if not isinstance(chart, Chart):
            error("Invalid input: chart must be an instance of Chart")
            raise ValueError("chart must be an instance of Chart")

        debug(f"Attempting to get_by_name with: {chart.name}")
        existing_chart = self.chart_dao.get_by_name(chart.name)

        if existing_chart is None:
            info(f"Chart '{chart.name}' not found. Creating new Chart.")
            new_chart = self.chart_dao.create(chart)
            info(f"New Chart created: {new_chart}")
            return new_chart
        critical(f"An error occurred while processing Chart: {e}")
        raise ValueError(f"Chart with name '{chart.name}' already exists.")

    def parse_local_chartlist(self) -> Optional[Chart]:
        """解析本地榜单文件"""

        # 读取榜单
        markdown_reader_name = self.get_default_markdown_reader_name()
        reader = self.get_reader(markdown_reader_name)

        chart_list = reader.read_files()
        info(f"读取了 {len(chart_list)} 个文件")

        return chart_list

    def get_reader(self, chart_file_type: str):
        reader = self.readers.get(chart_file_type)
        if not reader:
            error(f"不支持的榜单类型: {chart_file_type}")
            raise ValueError(f"不支持的榜单类型: {chart_file_type}")
        return reader

    def register_reader(self, markdown_reader_name: str, reader: MarkdownReader):
        """注册新的榜单读取器"""
        self.readers[markdown_reader_name] = reader
        info(f"Registered new reader for chart type: {markdown_reader_name}")

    # ------------------use end----------------------








