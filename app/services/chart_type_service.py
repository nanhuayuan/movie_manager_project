from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional

from app.config.app_config import AppConfig
from app.dao import  ChartTypeDAO
from app.model.chart_file_type_enun import ChartFileType
from app.model.db.movie_model import  ChartType
from app.services.base_service import BaseService
from app.utils.log_util import debug, info, warning, error, critical
from app.utils.read_markdown_file.markdown_reader import MarkdownReader


@dataclass
class ChartTypeService(BaseService[ChartType, ChartTypeDAO]):
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
        debug("ChartTypeService post-initialization completed")

    def __init__(self):
        super().__init__()

        self.config = AppConfig().get_chart_type_config()
        debug(f"Loaded configuration: {self.config}")

        self.name = self.config.get('name', '')
        self.description = self.config.get('description', '')

        self.chart_type_dao = ChartTypeDAO()
        self.chart_type = ChartType(
            name=self.name,
            description=self.description,

        )
        info(f"ChartTypeService initialized with chart_type: {self.chart_type}")

    def get_by_name_or_create(self, chart_type: ChartType = None) -> Optional[ChartType]:
        """
        根据名称获取ChartType，如果不存在则创建新的ChartType

        Args:
            chart_type (ChartType, optional): 要获取或创建的ChartType对象。如果为None，则使用默认的chart_type。

        Returns:
            Optional[ChartType]: 获取到的或新创建的ChartType对象，如果出现错误则返回None

        Raises:
            ValueError: 当输入的chart_type不是ChartType实例时抛出
        """
        debug(f"Entering get_by_name_or_create with chart_type: {chart_type}")

        if chart_type is None:
            chart_type = self.get_current_chart_type()
            debug(f"Using default chart_type: {chart_type}")

        if not isinstance(chart_type, ChartType):
            error("Invalid input: chart_type must be an instance of ChartType")
            raise ValueError("chart_type must be an instance of ChartType")

        try:
            debug(f"Attempting to get_by_name with: {chart_type.name}")
            existing_chart_type = self.chart_type_dao.get_by_name(chart_type.name)

            if existing_chart_type is None:
                info(f"ChartType '{chart_type.name}' not found. Creating new ChartType.")
                new_chart_type = self.chart_type_dao.create(chart_type)
                info(f"New ChartType created: {new_chart_type}")
                return new_chart_type
            else:
                info(f"Existing ChartType found: {existing_chart_type}")
                return existing_chart_type
        except Exception as e:
            critical(f"An error occurred while processing ChartType: {e}")
            return None

    def get_current_chart_type(self):
        return self.chart_type
