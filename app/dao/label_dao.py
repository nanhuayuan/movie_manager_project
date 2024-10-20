# app/dao/label_dao.py
from .base_dao import BaseDAO
from app.model.db.movie_model  import Label

class LabelDAO(BaseDAO[Label]):
    def __init__(self):
        super().__init__()
