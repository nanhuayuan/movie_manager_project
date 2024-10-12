import json
from typing import Optional

from app.dao.movie_dao import MovieDAO
from app.dao.magnet_dao import MagnetDAO
from app.model.db.movie_model import Movie
from app.services.cache_service import CacheService
from app.services.jellyfin_service import JellyfinService
from app.services.everything_service import EverythingService
from app.services.scraper_service import ScraperService
from app.services.qbittorrent_service import QBittorrentService
from app.utils.db_util import db
from app.utils.redis_client import RedisUtil
import logging


class MovieService:
    def __init__(self, movie_dao: MovieDAO = None, magnet_dao: MagnetDAO = None,
                 jellyfin_service: JellyfinService = None, everything_service: EverythingService = None,
                 scraper_service: ScraperService = None, qbittorrent_service: QBittorrentService = None,
                 redis_client: RedisUtil = None, cache_service: CacheService = None):

        # 如果传入参数为空，则创建默认对象
        self.movie_dao = movie_dao if movie_dao is not None else MovieDAO()
        self.magnet_dao = magnet_dao if magnet_dao is not None else MagnetDAO()
        self.jellyfin_service = jellyfin_service if jellyfin_service is not None else JellyfinService()
        self.everything_service = everything_service if everything_service is not None else EverythingService()
        self.scraper_service = scraper_service if scraper_service is not None else ScraperService()
        self.qbittorrent_service = qbittorrent_service if qbittorrent_service is not None else QBittorrentService()
        self.redis_client = redis_client if redis_client is not None else RedisUtil()

        self.logger = logging.getLogger(__name__)
        self.cache_service = cache_service if cache_service is not None else CacheService()

        self.cache_prefix = "movie:"  # 缓存键的前缀
        self.all_ids_key = "all_movie_ids"  # 所有电影ID的缓存键

    def get_movie(self, movie_id: str):
        """
        获取电影信息，优先从缓存中获取，如果缓存中没有则从数据库获取并缓存
        """
        # 尝试从缓存中获取电影信息
        cached_movie = self.redis_client.get(f"{self.cache_prefix}{movie_id}")
        if cached_movie:
            self.logger.info(f"Cache hit for movie {movie_id}")
            return json.loads(cached_movie)

        # 如果缓存中没有，从数据库获取
        movie = self.movie_dao.get(movie_id)
        if movie:
            # 将电影信息缓存到Redis，设置过期时间为1小时
            self.redis_client.setex(f"{self.cache_prefix}{movie_id}", 3600, json.dumps(movie))
            self.logger.info(f"Cached movie {movie_id}")
        return movie

    def process_movie_list(self, file_path: str):
        movies = self._read_movie_list(file_path)
        for movie in movies:
            self._process_single_movie(movie)

    def _process_single_movie(self, movie: dict):
        movie_id = movie['id']

        # 检查缓存和数据库中是否存在
        if not self.redis_client.exists(f"{self.cache_prefix}{movie_id}") and not self.movie_dao.exists(movie_id):
            self.movie_dao.add(movie)
            self.redis_client.setex(f"{self.cache_prefix}{movie_id}", 3600, json.dumps(movie))
            self.logger.info(f"Added and cached new movie {movie_id}")

        # 检查Jellyfin和本地是否存在
        if self.jellyfin_service.movie_exists(movie_id) or self.everything_service.file_exists(movie_id):
            self.movie_dao.update_status(movie_id, 'downloaded')
            # 更新缓存
            cached_movie = json.loads(self.redis_client.get(f"{self.cache_prefix}{movie_id}") or '{}')
            cached_movie['status'] = 'downloaded'
            self.redis_client.setex(f"{self.cache_prefix}{movie_id}", 3600, json.dumps(cached_movie))
            self.logger.info(f"Updated status for movie {movie_id} to 'downloaded'")
            return

        # 爬取电影信息
        movie_info = self.scraper_service.scrape_movie_info(movie_id)
        self.movie_dao.update(movie_id, movie_info)
        # 更新缓存
        self.redis_client.setex(f"{self.cache_prefix}{movie_id}", 3600, json.dumps(movie_info))
        self.logger.info(f"Updated movie info for {movie_id}")

        # 获取磁力链接
        magnets = self.scraper_service.get_magnets(movie_id)
        for magnet in magnets:
            self.magnet_dao.add(movie_id, magnet)

        # 下载电影
        self._download_movie(movie_id, magnets)

    def _download_movie(self, movie_id: str, magnets: list):
        for magnet in magnets:
            torrent_hash = self.qbittorrent_service.add_torrent(magnet)
            if self.qbittorrent_service.check_download_speed(torrent_hash):
                self.movie_dao.update_status(movie_id, 'downloading')
                # 更新缓存
                cached_movie = json.loads(self.redis_client.get(f"{self.cache_prefix}{movie_id}") or '{}')
                cached_movie['status'] = 'downloading'
                self.redis_client.setex(f"{self.cache_prefix}{movie_id}", 3600, json.dumps(cached_movie))
                self.logger.info(f"Started downloading movie {movie_id}")
                return
            else:
                self.qbittorrent_service.remove_torrent(torrent_hash)

        self.logger.warning(f"Failed to find a working magnet for movie {movie_id}")
        self.movie_dao.update_status(movie_id, 'failed')
        # 更新缓存
        cached_movie = json.loads(self.redis_client.get(f"{self.cache_prefix}{movie_id}") or '{}')
        cached_movie['status'] = 'failed'
        self.redis_client.setex(f"{self.cache_prefix}{movie_id}", 3600, json.dumps(cached_movie))

    def get_all_movies(self):
        """
        获取所有电影信息，优先从缓存中获取
        """
        # 尝试从缓存中获取所有电影ID
        cached_movie_ids = self.redis_client.smembers("all_movie_ids")
        if cached_movie_ids:
            self.logger.info("Cache hit for all movie IDs")
            movies = []
            for movie_id in cached_movie_ids:
                movie = self.get_movie(movie_id.decode())  # Redis返回的是字节字符串
                if movie:
                    movies.append(movie)
            return movies

        # 如果缓存中没有，从数据库获取
        movies = self.movie_dao.get_all()
        # 缓存所有电影ID和详细信息
        pipeline = self.redis_client.pipeline()
        for movie in movies:
            movie_id = movie['id']
            pipeline.sadd("all_movie_ids", movie_id)
            pipeline.setex(f"{self.cache_prefix}{movie_id}", 3600, json.dumps(movie))
        pipeline.execute()
        self.logger.info("Cached all movie IDs and details")
        return movies



