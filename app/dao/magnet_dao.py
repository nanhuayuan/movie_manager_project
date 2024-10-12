# app/dao/magnet_dao.py
from .base_dao import BaseDAO
from app.model.db.movie_model  import Magnet
from sqlalchemy import desc

class MagnetDAO(BaseDAO[Magnet]):
    def __init__(self):
        super().__init__(Magnet)

    def get_by_movie_id(self, movie_id: str) -> list[Magnet]:
        return db.session.query(Magnet).filter(Magnet.mid == movie_id).order_by(desc(Magnet.date)).all()

    def get_by_magnet_xt(self, magnet_xt: str) -> Magnet:
        return db.session.query(Magnet).filter(Magnet.magnet_xt == magnet_xt).first()