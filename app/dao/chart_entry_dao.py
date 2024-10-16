# app/dao/chart_entry_dao.py
from typing import Optional

from sqlalchemy.exc import SQLAlchemyError

from .base_dao import BaseDAO
from app.model.db.movie_model import ChartEntry
from app.model.enums import DownloadStatus
from app.utils.log_util import debug, info, warning, error, critical

class ChartEntryDAO(BaseDAO[ChartEntry]):
    """
    ChartEntry数据访问对象，处理与ChartEntry模型相关的数据库操作

    继承自BaseDAO，实现了单例模式
    """

    def __init__(self):
        """
        初始化ChartEntryDAO，设置模型为ChartEntry

        日志记录：
        - 记录ChartEntryDAO的初始化，便于追踪DAO对象的创建
        """
        super().__init__(ChartEntry)
        info("ChartEntryDAO initialized")

    def get_chart_entry_by_movie_id_and_chart_id(self, chart_entry: ChartEntry) -> Optional[ChartEntry]:
        """
        根据电影ID和榜单ID获取榜单条目

        Args:
            chart_entry (ChartEntry): 包含movie_id和chart_id的ChartEntry对象

        Returns:
            Optional[ChartEntry]: 如果找到则返回ChartEntry对象，否则返回None

        日志记录：
        - 记录尝试获取榜单条目的操作
        - 记录是否成功找到榜单条目
        - 记录可能发生的各种错误
        """
        try:
            debug(f"Attempting to get chart entry for movie_id: {chart_entry.movie_id} and chart_id: {chart_entry.chart_id}")
            # 定义 criteria 字典
            criteria = {'movie_id': chart_entry.movie_id, 'chart_id': chart_entry.chart_id}

            # 类型检查
            if not isinstance(chart_entry, ChartEntry):
                raise ValueError("chart_entry must be an instance of ChartEntry")

            # 查询数据
            chart_entry_list = self.find_by_criteria(criteria)

            # 检查结果
            if chart_entry_list and len(chart_entry_list) > 0:
                info(f"Chart entry found for movie_id: {chart_entry.movie_id} and chart_id: {chart_entry.chart_id}")
                return chart_entry_list[0]
            else:
                info(f"No chart entry found for movie_id: {chart_entry.movie_id} and chart_id: {chart_entry.chart_id}")
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

    def get_by_chart_and_movie(self, chart_id: int, movie_id: int) -> Optional[ChartEntry]:
        """
        根据榜单ID和电影ID获取榜单条目

        Args:
            chart_id (int): 榜单ID
            movie_id (int): 电影ID

        Returns:
            Optional[ChartEntry]: 如果找到则返回ChartEntry对象，否则返回None

        日志记录：
        - 记录尝试获取榜单条目的操作
        - 记录是否成功找到榜单条目
        """
        debug(f"Getting chart entry for chart_id: {chart_id} and movie_id: {movie_id}")
        entry = self.db.session.query(ChartEntry).filter(
            ChartEntry.chart_id == chart_id,
            ChartEntry.movie_id == movie_id
        ).first()
        if entry:
            info(f"Chart entry found for chart_id: {chart_id} and movie_id: {movie_id}")
        else:
            info(f"No chart entry found for chart_id: {chart_id} and movie_id: {movie_id}")
        return entry

    def update_status(self, entry_id: int, status: DownloadStatus) -> bool:
        """
        更新榜单条目的下载状态

        Args:
            entry_id (int): 榜单条目ID
            status (DownloadStatus): 新的下载状态

        Returns:
            bool: 更新成功返回True，否则返回False

        日志记录：
        - 记录尝试更新榜单条目状态的操作
        - 记录更新操作是否成功
        - 记录可能发生的错误
        """
        try:
            debug(f"Attempting to update status for entry_id: {entry_id} to {status}")
            entry = self.get_by_id(entry_id)
            if entry:
                entry.status = status
                self.db.session.commit()
                info(f"Successfully updated status for entry_id: {entry_id} to {status}")
                return True
            else:
                warning(f"Entry not found for entry_id: {entry_id}")
            return False
        except SQLAlchemyError as e:
            error(f"SQLAlchemyError while updating status: {e}")
            self.db.session.rollback()
            return False
        except Exception as e:
            error(f"Unexpected error while updating status: {e}")
            return False