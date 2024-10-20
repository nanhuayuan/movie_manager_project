from .base_dao import BaseDAO
from app.model.db.movie_model import MovieSery as MovieSeries

class MovieSeriesDAO(BaseDAO[MovieSeries]):
    def __init__(self):
        super().__init__()

    def get_by_movie_and_series(self, movie_id: int, series_id: int) -> MovieSeries:
        return db.session.query(MovieSeries).filter(
            MovieSeries.movie_id == movie_id,
            MovieSeries.series_id == series_id
        ).first()

    def get_series_by_movie(self, movie_id: int) -> list[MovieSeries]:
        return db.session.query(MovieSeries).filter(MovieSeries.movie_id == movie_id).all()

    def get_movies_by_series(self, series_id: int) -> list[MovieSeries]:
        return db.session.query(MovieSeries).filter(MovieSeries.series_id == series_id).all()