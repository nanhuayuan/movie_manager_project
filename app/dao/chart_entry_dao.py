# app/dao/chart_entry_dao.py
from typing import Optional

from sqlalchemy.exc import SQLAlchemyError

from .base_dao import BaseDAO
from app.model.db.movie_model import ChartEntry
from app.model.enums import DownloadStatus
from ..utils.log_util import error


class ChartEntryDAO(BaseDAO[ChartEntry]):
    def __init__(self):
        super().__init__(ChartEntry)

    def get_chart_entry_by_movie_id_and_chart_id(self, chart_entry: ChartEntry) -> Optional[ChartEntry]:
        try:
            # 定义 criteria 字典
            criteria = {'movie_id': chart_entry.movie_id, 'chart_id': chart_entry.chart_id}

            # 类型检查
            if not isinstance(chart_entry, ChartEntry):
                raise ValueError("chart_entry must be an instance of ChartEntry")

            # 查询数据
            chart_entry_list = self.find_by_criteria(criteria)

            # 检查结果
            if chart_entry_list and len(chart_entry_list) > 0:
                return chart_entry_list[0]
            else:
                return None

        except NameError as e:
            error(f"Error: {e}")
            return None
        except TypeError as e:
            error(f"Error: {e}")
            return None
        except IndexError as e:
            error(f"Error: {e}")
            return None

    def get_by_chart_and_movie(self, chart_id: int, movie_id: int) -> ChartEntry:
        return self.db.session.query(ChartEntry).filter(
            ChartEntry.chart_id == chart_id,
            ChartEntry.movie_id == movie_id
        ).first()

    def update_status(self, entry_id: int, status: DownloadStatus) -> bool:
        try:
            entry = self.get_by_id(entry_id)
            if entry:
                entry.status = status
                self.db.session.commit()
                return True
            return False
        except SQLAlchemyError as e:
            self.session.rollback()
            raise e