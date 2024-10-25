from dataclasses import dataclass
from typing import Optional

from app.dao import ChartEntryDAO
from app.model.db.movie_model import ChartEntry, Movie
from app.utils.download_client import DownloadStatus
from app.services.base_service import BaseService
from app.config.log_config import debug, info, warning, error, critical


@dataclass
class ChartEntryService(BaseService[ChartEntry, ChartEntryDAO]):
    def __init__(self):
        super().__init__()
        info("ChartEntryService initialized")

    def get_by_chart_and_movie(self, chart_id: int, movie_id: int) -> Optional[ChartEntry]:
        """
        根据榜单ID和电影ID获取榜单条目（每个电影只可能有一个榜单）
        Args:
            chart_id (int): 榜单ID
            movie_id (int): 电影ID
        Returns:
            Optional[ChartEntry]: 如果找到则返回ChartEntry对象，否则返回None
        日志记录：
        - 记录尝试获取榜单条目的操作
        - 记录是否成功找到榜单条目
        """
        try:
            # 定义 criteria 字典
            criteria = {'movie_id': movie_id, 'chart_id': chart_id}

            # 查询数据
            chart_entry_list = self.dao.find_by_criteria(criteria)

            # 检查结果
            if chart_entry_list and len(chart_entry_list) > 0:
                info(f"Chart entry found for movie_id: {movie_id} and chart_id: {chart_id}")
                return chart_entry_list[0]
            else:
                info(f"No chart entry found for movie_id: {movie_id} and chart_id: {chart_id}")
                return None
        except ValueError as e:
            error(f"ValueError: {e}")
            return None
        except TypeError as e:
            error(f"TypeError: {e}")
            return None
        except IndexError as e:
            error(f"IndexError: {e}")
            return None
        except Exception as e:
            error(f"Unexpected error: {e}")
            return None
