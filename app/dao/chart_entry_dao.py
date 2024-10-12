# app/dao/chart_entry_dao.py
from sqlalchemy.exc import SQLAlchemyError

from .base_dao import BaseDAO
from app.model.db.movie_model  import ChartEntry

from ..model.enums import DownloadStatus
from ..utils.db_util import db


class ChartEntryDAO(BaseDAO[ChartEntry]):
    def __init__(self):
        super().__init__(ChartEntry)

    def get_by_chart_and_movie(self, chart_id: int, movie_id: int) -> ChartEntry:
        return db.session.query(ChartEntry).filter(
            ChartEntry.chart_id == chart_id,
            ChartEntry.movie_id == movie_id
        ).first()

    def update_status(self, entry_id: int, status: DownloadStatus) -> bool:
        try:
            entry = self.get_by_id(entry_id)
            if entry:
                entry.status = status
                db.session.commit()
                return True
            return False
        except SQLAlchemyError as e:
            db.session.rollback()
            raise e