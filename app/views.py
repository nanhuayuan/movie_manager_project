from flask import Blueprint, request, jsonify
from app.schemas import MovieSchema
from app.di import dependency_container

movie_bp = Blueprint('movies', __name__)
movie_service = dependency_container.movie_service
movie_schema = MovieSchema()
movies_schema = MovieSchema(many=True)

@movie_bp.route('/movies', methods=['GET'])
def get_movies():
    movies = movie_service.get_all_movies()
    return movies_schema.jsonify(movies)

@movie_bp.route('/movies', methods=['POST'])
def create_movie():
    data = request.json
    movie = movie_service.create_movie(data)
    return movie_schema.jsonify(movie), 201
