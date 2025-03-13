from typing import Optional, List, Dict, Any
import logging
from app.config.app_config import AppConfig
from app.utils.jellyfin_client import BaseJellyfinClient, JellyfinApiClient, JellyfinApiclientPythonClient


class JellyfinService:
    def __init__(self):
        self.config = AppConfig().get_jellyfin_config()
        self.client = self._create_client()
        self.retry_count = self.config.get('retry_count', 3)
        logging.info("Jellyfin 服务已初始化")

    def _create_client(self) -> BaseJellyfinClient:
        """创建 Jellyfin 客户端"""
        client_type = self.config.get('client_type', 'api')
        client_map = {
            'jellyfinapi': JellyfinApiClient,
            'jellyfin-apiclient-python': JellyfinApiclientPythonClient
        }

        client_class = client_map.get(client_type)
        if not client_class:
            raise ValueError(f"不支持的 Jellyfin 客户端类型: {client_type}")

        return client_class(
            api_url=self.config.get('api_url'),
            api_key=self.config.get('api_key'),
            user_id=self.config.get('user_id', ''),
            item_id=self.config.get('item_id', ''),
            playlists_id=self.config.get('playlists_id', '')
        )

    def _retry_operation(self, operation, *args, **kwargs):
        """执行操作并在失败时重试"""
        for attempt in range(self.retry_count):
            try:
                return operation(*args, **kwargs)
            except Exception as e:
                if attempt == self.retry_count - 1:
                    logging.error(f"操作失败，已尝试 {self.retry_count} 次: {str(e)}")
                    raise
                logging.warning(f"操作失败，正在重试 ({attempt + 1}/{self.retry_count}): {str(e)}")
        return None

    def check_movie_exists(self, title: str) -> bool:
        """检查电影是否存在于 Jellyfin 库中"""
        movies = self._retry_operation(self.search_by_serial_number, title)
        exists = movies is not None
        logging.info(f"电影 '{title}' {'存在' if exists else '不存在'} 于 Jellyfin 库中")
        return exists

    def search_movie(self, title: str, user_id: str = '') -> Optional[Dict]:
        """搜索电影"""
        return self._retry_operation(self.client.search_movie, title, user_id)

    def get_movie_info(self, title: str) -> Optional[Dict]:
        """获取电影信息"""
        movie = self._retry_operation(self.client.search_movie, title)
        if movie and ('Id' in movie or 'id' in movie):
            movie_id = movie.get('Id', movie.get('id'))
            return self._retry_operation(self.client.get_movie_details, movie_id)
        logging.info(f"未能获取电影 '{title}' 的信息")
        return None

    def get_all_movies_info(self, user_id: str = '') -> List[Dict]:
        """获取所有电影信息"""
        movies = self._retry_operation(self.client.get_all_movie_info, user_id)
        logging.info(f"获取到 {len(movies)} 部电影的信息")
        return movies

    def get_movie_details_by_id(self, movie_id,user_id: str = '') -> List[Dict]:
        """获取所有电影信息"""
        movie = self._retry_operation(self.client.get_movie_details, movie_id)
        logging.info(f"获取到 {movie.name} 电影的信息")
        return movie

    def delete_movie_by_id(self, movie_id: str, user_id: str = '') -> bool:
        """根据ID删除电影"""
        return self._retry_operation(self.client.delete_movie_by_id, movie_id, user_id)

    def search_by_serial_number(self, serial_number: str, user_id: str = '') -> List:
        """根据序列号搜索电影"""
        return self._retry_operation(self.client.search_by_serial_number, serial_number, user_id)

    def get_existing_playlists(self, user_id: str = '') -> List[Dict[str, Any]]:
        """获取现有播放列表"""
        return self._retry_operation(self.client.get_existing_playlists, user_id)

    def get_playlist_id(self, playlist_name: str, user_id: str = '') -> str:
        """获取播放列表ID，如果不存在则创建"""
        return self._retry_operation(self.client.get_playlist_id, playlist_name, user_id)

    def add_to_playlist(self, playlist_id: str, ids: str, user_id: str = '') -> bool:
        """将电影添加到播放列表"""
        return self._retry_operation(self.client.add_to_playlist, playlist_id, ids, user_id)
