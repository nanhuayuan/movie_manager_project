from flask import Blueprint, request, jsonify
from flask_marshmallow import Marshmallow
from dependency_injector.wiring import inject, Provide
from app.services.movie_service import MovieService
from app.container import Container
from app.schemas.movie_schema import MovieSchema
import logging

# 创建一个Blueprint用于组织和管理与电影相关的路由
movie_bp = Blueprint('movie', __name__)
ma = Marshmallow()


class MovieController:
    """
    MovieController 类负责处理与电影相关的HTTP请求。
    它使用依赖注入来获取必要的服务，并定义了处理不同电影操作的路由。
    """

    @inject
    def __init__(self, movie_service: MovieService = Provide[Container.movie_service]):
        self.movie_service = movie_service

    @movie_bp.route('/process', methods=['POST'])
    @inject
    def process_movie_list(self,movie_service: MovieService = Provide[Container.movie_service]):
        """
        处理电影列表文件的POST请求。

        期望请求体中包含 'file_path' 字段，指定要处理的文件路径。

        :param movie_service: 注入的MovieService实例
        :return: JSON响应表示处理状态
        """
        file_path = request.json.get('file_path')
        if not file_path:
            return jsonify({'error': 'File path is required'}), 400

        try:
            movie_service.process_movie_list(file_path)
            return jsonify({'message': 'Movie list processing started'}), 202
        except Exception as e:
            logging.error(f"Error processing movie list: {str(e)}")
            return jsonify({'error': 'An error occurred while processing the movie list'}), 500

    @movie_bp.route('/movie/<string:movie_id>', methods=['GET'])
    @inject
    def get_movie(movie_id: str):
        """
        获取单个电影信息的GET请求。

        :param movie_id: 要获取的电影ID
        :param movie_service: 注入的MovieService实例
        :return: JSON响应包含电影信息或错误信息
        """
        try:
            movie = self.movie_service.get_movie(movie_id)
            if not movie:
                return jsonify({'error': 'Movie not found'}), 404
            return jsonify(MovieSchema().dump(movie)), 200
        except Exception as e:
            logging.error(f"Error retrieving movie {movie_id}: {str(e)}")
            return jsonify({'error': 'An error occurred while retrieving the movie'}), 500

    @movie_bp.route('/movie/<string:movie_id>/download', methods=['POST'])
    @inject
    def download_movie(movie_id: str):
        """
        开始下载特定电影的POST请求。

        :param movie_id: 要下载的电影ID
        :param movie_service: 注入的MovieService实例
        :return: JSON响应表示下载状态
        """
        try:
            self.movie_service.download_movie(movie_id)
            return jsonify({'message': 'Movie download started'}), 202
        except Exception as e:
            logging.error(f"Error starting download for movie {movie_id}: {str(e)}")
            return jsonify({'error': 'An error occurred while starting the movie download'}), 500

    @movie_bp.route('/movies', methods=['GET'])
    @inject
    def get_all_movies(movie_service: MovieService = Provide[Container.movie_service]):
        """
        获取所有电影信息的GET请求。

        :param movie_service: 注入的MovieService实例
        :return: JSON响应包含所有电影信息或错误信息
        """
        try:
            movies = movie_service.get_all_movies()
            return jsonify(MovieSchema(many=True).dump(movies)), 200
        except Exception as e:
            logging.error(f"Error retrieving all movies: {str(e)}")
            return jsonify({'error': 'An error occurred while retrieving movies'}), 500


def init_app(app):
    """
    初始化函数，用于在Flask应用中注册这个Blueprint。

    :param app: Flask应用实例
    """
    app.register_blueprint(movie_bp, url_prefix='/api/movies')