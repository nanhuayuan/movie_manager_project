# app/dao/series_dao.py
from .base_dao import BaseDAO
from app.model.db.movie_model  import Series

class SeriesDAO(BaseDAO[Series]):
    def __init__(self):
        super().__init__()
