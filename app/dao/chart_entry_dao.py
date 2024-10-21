# app/dao/chart_entry_dao.py
from typing import Optional

from sqlalchemy.exc import SQLAlchemyError

from .base_dao import BaseDAO
from app.model.db.movie_model import ChartEntry
from app.model.enums import DownloadStatus
from app.config.log_config import debug, info, warning, error, critical

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
        super().__init__()
        info("ChartEntryDAO initialized")



    # ------------------use end----------------------
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