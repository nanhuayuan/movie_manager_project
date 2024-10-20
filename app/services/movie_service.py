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
from app.utils.log_util import debug, info, warning, error, critical


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

    def exists_movie(self, serial_number: str):
        # jellyfin是否存在
        jellyfin_exists = self.jellyfin_service.check_movie_exists(serial_number)

        if jellyfin_exists:
            info("serial_number:{} 存在jellyfin", serial_number)
        else:
            info("serial_number:{} 不存在jellyfin", serial_number)

        # 本地存在的，才叫存在
        # everything检查本地是否存在
        everything_exists = self.everything_service.check_movie_exists(serial_number)
        if everything_exists:
            info("serial_number:{} 存在本地文件", serial_number)
        else:
            info("serial_number:{} 不存在本地文件", serial_number)

        return everything_exists

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

    def process_movie_list(self, file_path: str):
        """处理电影列表文件"""
        info(f"Processing movie list from file: {file_path}")
        movies = self._read_movie_list(file_path)
        for movie in movies:
            self._process_single_movie(movie)

    def _process_single_movie(self, movie: dict):
        """处理单个电影信息"""
        movie_id = movie['id']
        debug(f"Processing movie: {movie_id}")

        # 检查缓存和数据库中是否存在
        if not self.redis_client.exists(f"{self.cache_prefix}{movie_id}") and not self.movie_dao.exists(movie_id):
            self.movie_dao.add(movie)
            self.redis_client.setex(f"{self.cache_prefix}{movie_id}", 3600, json.dumps(movie))
            info(f"Added and cached new movie {movie_id}")

        # 检查Jellyfin和本地是否存在
        if self.jellyfin_service.movie_exists(movie_id) or self.everything_service.file_exists(movie_id):
            self._update_movie_status(movie_id, 'downloaded')
            return

        # 爬取电影信息
        movie_info = self.scraper_service.scrape_movie_info(movie_id)
        self.movie_dao.update(movie_id, movie_info)
        self._update_cache(movie_id, movie_info)
        info(f"Updated movie info for {movie_id}")

        # 获取磁力链接
        magnets = self.scraper_service.get_magnets(movie_id)
        for magnet in magnets:
            self.magnet_dao.add(movie_id, magnet)

        # 下载电影
        self._download_movie(movie_id, magnets)

    def _download_movie(self, movie_id: str, magnets: list):
        """尝试下载电影"""
        info(f"Attempting to download movie: {movie_id}")
        for magnet in magnets:
            torrent_hash = self.qbittorrent_service.add_torrent(magnet)
            if self.qbittorrent_service.check_download_speed(torrent_hash):
                self._update_movie_status(movie_id, 'downloading')
                info(f"Started downloading movie {movie_id}")
                return
            else:
                self.qbittorrent_service.remove_torrent(torrent_hash)
                warning(f"Removed non-working torrent for movie {movie_id}")

        error(f"Failed to find a working magnet for movie {movie_id}")
        self._update_movie_status(movie_id, 'failed')

    def _update_movie_status(self, movie_id: str, status: str):
        """更新电影状态并刷新缓存"""
        self.movie_dao.update_status(movie_id, status)
        cached_movie = json.loads(self.redis_client.get(f"{self.cache_prefix}{movie_id}") or '{}')
        cached_movie['status'] = status
        self._update_cache(movie_id, cached_movie)
        info(f"Updated status for movie {movie_id} to '{status}'")

    def _update_cache(self, movie_id: str, movie_data: dict):
        """更新电影缓存"""
        self.redis_client.setex(f"{self.cache_prefix}{movie_id}", 3600, json.dumps(movie_data))
        debug(f"Updated cache for movie {movie_id}")

    def get_all_movies(self):
        """获取所有电影信息，优先从缓存中获取"""
        debug("Attempting to get all movies")
        # 尝试从缓存中获取所有电影ID
        cached_movie_ids = self.redis_client.smembers(self.all_ids_key)
        if cached_movie_ids:
            info("Cache hit for all movie IDs")
            movies = []
            for movie_id in cached_movie_ids:
                movie = self.get_movie(movie_id.decode())  # Redis返回的是字节字符串
                if movie:
                    movies.append(movie)
            return movies

        # 如果缓存中没有，从数据库获取
        info("Cache miss for all movie IDs, fetching from database")
        movies = self.movie_dao.get_all()
        # 缓存所有电影ID和详细信息
        pipeline = self.redis_client.pipeline()
        for movie in movies:
            movie_id = movie['id']
            pipeline.sadd(self.all_ids_key, movie_id)
            pipeline.setex(f"{self.cache_prefix}{movie_id}", 3600, json.dumps(movie))
        pipeline.execute()
        info("Cached all movie IDs and details")
        return movies

    def _read_movie_list(self, file_path: str):
        """读取电影列表文件"""
        # 这个方法的实现没有在原代码中给出，所以这里只添加一个日志
        info(f"Reading movie list from file: {file_path}")
        # 实现读取文件的逻辑...
        return []  # 返回读取到的电影列表
