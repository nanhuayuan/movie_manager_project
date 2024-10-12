# app/dao/genre_dao.py
from .base_dao import BaseDAO
from app.model.db.movie_model  import Genre

class GenreDAO(BaseDAO[Genre]):
    def __init__(self):
        super().__init__(Genre)

    def get_by_name(self, name: str) -> Genre:
        return db.session.query(Genre).filter(Genre.name == name).first()
