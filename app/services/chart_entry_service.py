from dataclasses import dataclass
from typing import Optional, Dict, Any, TypeVar, Tuple

from app.dao import ChartEntryDAO
from app.model.db.movie_model import ChartEntry, Movie
from app.utils.download_client import DownloadStatus
from app.services.base_service import BaseService
from app.config.log_config import debug, info, warning, error, critical

T = TypeVar('T')  # 类型变量用于泛型方法


@dataclass
class ChartEntryService(BaseService[ChartEntry, ChartEntryDAO]):
    def __init__(self):
        super().__init__()
        info("ChartEntryService initialized")

    def _get_by_chart_and_entity(self, chart_id: int, entity_id: int, entity_type: str) -> Optional[ChartEntry]:
        """
        通用方法：根据榜单ID和实体ID获取榜单条目

        Args:
            chart_id (int): 榜单ID
            entity_id (int): 实体ID (电影ID或演员ID)
            entity_type (str): 实体类型 ("movie" 或 "actor")

        Returns:
            Optional[ChartEntry]: 如果找到则返回ChartEntry对象，否则返回None

        日志记录：
        - 记录尝试获取榜单条目的操作
        - 记录是否成功找到榜单条目
        """
        try:
            # 定义 criteria 字典
            criteria = {f'{entity_type}_id': entity_id, 'chart_id': chart_id}

            # 查询数据
            chart_entry_list = self.dao.find_by_criteria(criteria)

            # 检查结果
            if chart_entry_list and len(chart_entry_list) > 0:
                info(f"Chart entry found for {entity_type}_id: {entity_id} and chart_id: {chart_id}")
                return chart_entry_list[0]
            else:
                info(f"No chart entry found for {entity_type}_id: {entity_id} and chart_id: {chart_id}")
                return None
        except Exception as e:
            error(f"{type(e).__name__}: {e}")
            return None

    def get_by_chart_and_movie(self, chart_id: int, movie_id: int) -> Optional[ChartEntry]:
        """
        根据榜单ID和电影ID获取榜单条目（每个电影只可能有一个榜单）

        Args:
            chart_id (int): 榜单ID
            movie_id (int): 电影ID

        Returns:
            Optional[ChartEntry]: 如果找到则返回ChartEntry对象，否则返回None
        """
        return self._get_by_chart_and_entity(chart_id, movie_id, "movie")

    def get_by_chart_and_actor(self, chart_id: int, actor_id: int) -> Optional[ChartEntry]:
        """
        根据榜单ID和演员ID获取榜单条目

        Args:
            chart_id (int): 榜单ID
            actor_id (int): 演员ID

        Returns:
            Optional[ChartEntry]: 如果找到则返回ChartEntry对象，否则返回None
        """
        return self._get_by_chart_and_entity(chart_id, actor_id, "actor")