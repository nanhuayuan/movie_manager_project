# app/dao/chart_history_dao.py
from .base_dao import BaseDAO
from app.model.db.movie_model  import ChartHistory
from sqlalchemy import desc

class ChartHistoryDAO(BaseDAO[ChartHistory]):
    def __init__(self):
        super().__init__()

    def get_by_chart_and_movie(self, chart_id: int, movie_id: int) -> list[ChartHistory]:
        return db.session.query(ChartHistory).filter(
            ChartHistory.chart_id == chart_id,
            ChartHistory.movie_id == movie_id
        ).order_by(desc(ChartHistory.recorded_at)).all()

    def get_latest_by_chart(self, chart_id: int) -> list[ChartHistory]:
        subquery = db.session.query(
            ChartHistory.movie_id,
            func.max(ChartHistory.recorded_at).label('max_date')
        ).filter(ChartHistory.chart_id == chart_id).group_by(ChartHistory.movie_id).subquery()

        return db.session.query(ChartHistory).join(
            subquery,
            and_(
                ChartHistory.movie_id == subquery.c.movie_id,
                ChartHistory.recorded_at == subquery.c.max_date
            )
        ).filter(ChartHistory.chart_id == chart_id).all()