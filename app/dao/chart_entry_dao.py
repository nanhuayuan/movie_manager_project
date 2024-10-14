# app/dao/chart_entry_dao.py
from typing import Optional

from sqlalchemy.exc import SQLAlchemyError

from .base_dao import BaseDAO
from app.model.db.movie_model import ChartEntry
from app.model.enums import DownloadStatus
#from app import db  # 假设您的 Flask-SQLAlchemy 实例在 app/__init__.py 中定义

class ChartEntryDAO(BaseDAO[ChartEntry]):
    def __init__(self):
        super().__init__(ChartEntry)

    def get_by_movie_id(self, movie_id: int) -> Optional[ChartEntry]:
        obj = self.db.session.query(ChartEntry).filter(ChartEntry.movie_id == movie_id).first()
        return obj

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
            db.session.rollback()
            raise e