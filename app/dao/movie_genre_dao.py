from .base_dao import BaseDAO
from app.model.db.movie_model import MovieGenre

class MovieGenreDAO(BaseDAO[MovieGenre]):
    def __init__(self):
        super().__init__()

    def get_by_movie_and_genre(self, movie_id: int, genre_id: int) -> MovieGenre:
        return db.session.query(MovieGenre).filter(
            MovieGenre.movie_id == movie_id,
            MovieGenre.genre_id == genre_id
        ).first()

    def get_genres_by_movie(self, movie_id: int) -> list[MovieGenre]:
        return db.session.query(MovieGenre).filter(MovieGenre.movie_id == movie_id).all()

    def get_movies_by_genre(self, genre_id: int) -> list[MovieGenre]:
        return db.session.query(MovieGenre).filter(MovieGenre.genre_id == genre_id).all()