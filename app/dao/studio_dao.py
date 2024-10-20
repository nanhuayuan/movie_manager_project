from .base_dao import BaseDAO
from app.model.db.movie_model  import Studio

class StudioDAO(BaseDAO[Studio]):
    def __init__(self):
        super().__init__()
