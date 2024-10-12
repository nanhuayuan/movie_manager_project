# app/dao/movie_star_dao.py
from .base_dao import BaseDAO
from app.model.db.movie_model import MovieStar

class MovieStarDAO(BaseDAO[MovieStar]):
    def __init__(self):
        super().__init__(MovieStar)

    def get_by_movie_and_star(self, movie_id: int, star_id: int) -> MovieStar:
        return db.session.query(MovieStar).filter(
            MovieStar.movie_id == movie_id,
            MovieStar.star_id == star_id
        ).first()

    def get_stars_by_movie(self, movie_id: int) -> list[MovieStar]:
        return db.session.query(MovieStar).filter(MovieStar.movie_id == movie_id).all()

    def get_movies_by_star(self, star_id: int) -> list[MovieStar]:
        return db.session.query(MovieStar).filter(MovieStar.star_id == star_id).all()