import json
from typing import List

from app.dao.magnet_dao import MagnetDAO
from app.dao.movie_dao import MovieDAO
from app.model.db.movie_model import Movie
from app.services.base_service import BaseService
from app.services.cache_service import CacheService
from app.services.everything_service import EverythingService
from app.services.jellyfin_service import JellyfinService
from app.utils.redis_client import RedisUtil
from app.config.log_config import debug, info, warning, error, critical
from typing import Optional, List
from sqlalchemy.orm import Session
from datetime import datetime


class MovieService(BaseService[Movie, MovieDAO]):
    def __init__(self, movie_dao: MovieDAO = None, magnet_dao: MagnetDAO = None,
                 jellyfin_service: JellyfinService = None, everything_service: EverythingService = None,
                 redis_client: RedisUtil = None, cache_service: CacheService = None):
        super().__init__()

        # 初始化各种服务和DAO，如果没有提供则创建默认实例
        self.movie_dao = movie_dao if movie_dao is not None else MovieDAO()
        self.magnet_dao = magnet_dao if magnet_dao is not None else MagnetDAO()
        self.jellyfin_service = jellyfin_service if jellyfin_service is not None else JellyfinService()
        self.everything_service = everything_service if everything_service is not None else EverythingService()
        # self.scraper_service = scraper_service if scraper_service is not None else ScraperService()
        self.redis_client = redis_client if redis_client is not None else RedisUtil()
        self.cache_service = cache_service if cache_service is not None else CacheService()

        self.cache_prefix = "movie:"  # 缓存键的前缀
        self.all_ids_key = "all_movie_ids"  # 所有电影ID的缓存键

        info("MovieService initialized")

    def get_movie_from_db_by_serial_number(self, serial_number: str):
        # 定义 criteria 字典
        criteria = {'serial_number': serial_number}
        return self.dao.find_one_by_criteria(criteria)

    def jellyfin_exists_movie(self, serial_number: str):
        # jellyfin是否存在
        return self.jellyfin_service.check_movie_exists(serial_number)





    # ------------------use end----------------------
    def search_movies_by_rating(self, min_rating: float) -> List[Movie]:
        """按评分搜索电影"""
        try:
            debug(f"Searching movies with rating >= {min_rating}")
            return self.dao.find_by_criteria({'rating': {'$gte': min_rating}})
        except Exception as e:
            error(f"Error searching movies by rating: {str(e)}")
            return []

    def get_unwatched_movies(self) -> List[Movie]:
        """获取未观看的电影列表"""
        try:
            return self.dao.find_by_criteria({'watched': False})
        except Exception as e:
            error(f"Error getting unwatched movies: {str(e)}")
            return []

    def mark_as_downloaded(self, movie_id: int, download_path: str) -> bool:
        """标记电影为已下载状态"""
        try:
            movie = self.get_by_id(movie_id)
            if not movie:
                return False
            return bool(self.dao.update_by_id(movie_id, {
                'downloaded': True,
                'download_path': download_path,
                'download_time': datetime.now()
            }))
        except Exception as e:
            error(f"Error marking movie as downloaded: {str(e)}")
            return False

    def get_movie(self, movie_id: str):
        """
        获取电影信息，优先从缓存中获取，如果缓存中没有则从数据库获取并缓存
        """
        debug(f"Attempting to get movie with id: {movie_id}")
        # 尝试从缓存中获取电影信息
        cached_movie = self.redis_client.get(f"{self.cache_prefix}{movie_id}")
        if cached_movie:
            info(f"Cache hit for movie {movie_id}")
            return json.loads(cached_movie)

        # 如果缓存中没有，从数据库获取
        movie = self.movie_dao.get(movie_id)
        if movie:
            # 将电影信息缓存到Redis，设置过期时间为1小时
            self.redis_client.setex(f"{self.cache_prefix}{movie_id}", 3600, json.dumps(movie))
            info(f"Cached movie {movie_id}")
        else:
            warning(f"Movie {movie_id} not found in database")
        return movie


