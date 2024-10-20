# app/dao/movie_label_dao.py
from .base_dao import BaseDAO
from app.model.db.movie_model import MovieLabel

class MovieLabelDAO(BaseDAO[MovieLabel]):
    def __init__(self):
        super().__init__()

    def get_by_movie_and_label(self, movie_id: int, label_id: int) -> MovieLabel:
        return db.session.query(MovieLabel).filter(
            MovieLabel.movie_id == movie_id,
            MovieLabel.label_id == label_id
        ).first()

    def get_labels_by_movie(self, movie_id: int) -> list[MovieLabel]:
        return db.session.query(MovieLabel).filter(MovieLabel.movie_id == movie_id).all()

    def get_movies_by_label(self, label_id: int) -> list[MovieLabel]:
        return db.session.query(MovieLabel).filter(MovieLabel.label_id == label_id).all()