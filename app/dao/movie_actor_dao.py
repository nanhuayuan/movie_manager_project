# app/dao/movie_actor_dao.py
from .base_dao import BaseDAO
from app.model.db.movie_model import MovieActor

class MovieActorDAO(BaseDAO[MovieActor]):
    def __init__(self):
        super().__init__()

    def get_by_movie_and_star(self, movie_id: int, star_id: int) -> MovieActor:
        return db.session.query(MovieActor).filter(
            MovieActor.movie_id == movie_id,
            MovieActor.star_id == star_id
        ).first()

    def get_stars_by_movie(self, movie_id: int) -> list[MovieActor]:
        return db.session.query(MovieActor).filter(MovieActor.movie_id == movie_id).all()

    def get_movies_by_star(self, star_id: int) -> list[MovieActor]:
        return db.session.query(MovieActor).filter(MovieActor.star_id == star_id).all()