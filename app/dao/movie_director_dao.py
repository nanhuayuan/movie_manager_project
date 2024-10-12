# app/dao/movie_director_dao.py
from .base_dao import BaseDAO
from app.model.db.movie_model import MovieDirector

class MovieDirectorDAO(BaseDAO[MovieDirector]):
    def __init__(self):
        super().__init__(MovieDirector)

    def get_by_movie_and_director(self, movie_id: int, director_id: int) -> MovieDirector:
        return db.session.query(MovieDirector).filter(
            MovieDirector.movie_id == movie_id,
            MovieDirector.director_id == director_id
        ).first()

    def get_directors_by_movie(self, movie_id: int) -> list[MovieDirector]:
        return db.session.query(MovieDirector).filter(MovieDirector.movie_id == movie_id).all()

    def get_movies_by_director(self, director_id: int) -> list[MovieDirector]:
        return db.session.query(MovieDirector).filter(MovieDirector.director_id == director_id).all()