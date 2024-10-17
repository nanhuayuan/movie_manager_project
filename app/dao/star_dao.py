from .base_dao import BaseDAO
from app.model.db.movie_model  import Actor

class StarDAO(BaseDAO[Actor]):
    def __init__(self):
        super().__init__(Actor)

    def get_by_name(self, name: str) -> Actor:
        return db.session.query(Actor).filter(Actor.name == name).first()

    def update_favorite(self, star_id: int, favorite: int) -> bool:
        try:
            star = self.get_by_id(star_id)
            if star:
                star.favorite = favorite
                db.session.commit()
                return True
            return False
        except SQLAlchemyError as e:
            db.session.rollback()
            raise e