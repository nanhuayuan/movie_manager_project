# app/services/jellyfin_service.py
from app.utils.interfaces.jellyfin_util_interface import JellyfinUtilInterface
from app.utils.jellyfin_util import JellyfinUtil
from typing import Optional, List, Dict
import logging


class JellyfinService:
    """
    Jellyfin 服务类

    该类提供了高级的 Jellyfin 相关服务，使用 JellyfinUtilInterface 的实现
    来与 Jellyfin 服务器进行交互。

    Attributes:
        jellyfin_util (JellyfinUtilInterface): Jellyfin 工具接口的实现实例
    """

    def __init__(self, jellyfin_util: JellyfinUtilInterface = None):
        """
        初始化 Jellyfin 服务

        Args:
            jellyfin_util (JellyfinUtilInterface): Jellyfin 工具接口的实现实例
        """
        self.jellyfin_util = jellyfin_util if jellyfin_util is not None else JellyfinUtil()
        logging.info("Jellyfin 服务已初始化")

    def check_movie_exists(self, title: str) -> bool:
        """
        检查指定标题的电影是否存在于 Jellyfin 库中

        Args:
            title (str): 要检查的电影标题

        Returns:
            bool: 如果电影存在返回 True，否则返回 False

        Example:
            >>> service = JellyfinService(jellyfin_util)
            >>> service.check_movie_exists("The Matrix")
            True
        """
        # 使用工具接口搜索电影
        movie = self.search_by_serial_number(serial_number=title)
        exists = movie is not None

        # 记录搜索结果
        logging.info(f"电影 '{title}' {'存在' if exists else '不存在'} 于 Jellyfin 库中")
        return exists

    def get_movie_info(self, title: str) -> Optional[Dict]:
        """
        获取指定标题电影的详细信息

        Args:
            title (str): 要获取信息的电影标题

        Returns:
            Optional[Dict]: 如果找到电影，返回包含电影详细信息的字典；否则返回 None

        Example:
            >>> service = JellyfinService(jellyfin_util)
            >>> info = service.get_movie_info("The Matrix")
            >>> print(info['Name'])
            'The Matrix'
        """
        # 首先搜索电影
        movie = self.jellyfin_util.search_movie(title)

        # 如果找到电影且包含 ID，则获取详细信息
        if movie and 'Id' in movie:
            return self.jellyfin_util.get_movie_details(movie['Id'])

        # 如果未找到电影，记录日志并返回 None
        logging.info(f"未能获取电影 '{title}' 的信息")
        return None

    def get_all_movies_info(self) -> List[Dict]:
        """
        获取 Jellyfin 库中所有电影的信息

        Returns:
            List[Dict]: 包含所有电影信息的字典列表

        Example:
            >>> service = JellyfinService(jellyfin_util)
            >>> all_movies = service.get_all_movies_info()
            >>> print(len(all_movies))
            42
        """
        # 获取所有电影信息
        movies = self.jellyfin_util.get_all_movie_info()

        # 记录获取到的电影数量
        logging.info(f"获取到 {len(movies)} 部电影的信息")
        return movies

    def search_by_serial_number(self, serial_number: str, user_id: str = '') -> str:
        """
        根据番号搜索电影。
        """

        return self.jellyfin_util.search_by_serial_number(serial_number, user_id)
