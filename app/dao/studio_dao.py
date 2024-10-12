from .base_dao import BaseDAO
from app.model.db.movie_model  import Studio

class StudioDAO(BaseDAO[Studio]):
    def __init__(self):
        super().__init__(Studio)

    def get_by_name(self, name: str) -> Studio:
        return db.session.query(Studio).filter(Studio.name == name).first()