from app import ma
from app.model.db.movie_model import Movie

class MovieSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Movie
        load_instance = True
