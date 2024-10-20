from .base_dao import BaseDAO
from app.model.db.movie_model  import Actor

class ActorDAO(BaseDAO[Actor]):
    def __init__(self):
        super().__init__()


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