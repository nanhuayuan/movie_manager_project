# app/dao/director_dao.py
from .base_dao import BaseDAO
from app.model.db.movie_model import Director

class DirectorDAO(BaseDAO[Director]):
    def __init__(self):
        super().__init__()

