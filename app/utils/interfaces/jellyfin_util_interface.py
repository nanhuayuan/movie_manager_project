# app/interfaces/jellyfin_util_interface.py
from abc import ABC, abstractmethod
from typing import Optional, List, Dict


class JellyfinUtilInterface(ABC):
    """
    Jellyfin 工具接口类

    定义了与 Jellyfin 服务器交互所需的基本方法。
    所有实现此接口的类都必须提供这些方法的具体实现。
    """

    @abstractmethod
    def search_movie(self, title: str) -> Optional[Dict]:
        """
        搜索指定标题的电影

        Args:
            title (str): 要搜索的电影标题

        Returns:
            Optional[Dict]: 如果找到电影，返回包含电影信息的字典；否则返回 None
        """
        pass

    @abstractmethod
    def get_movie_details(self, movie_id: str) -> Optional[Dict]:
        """
        获取指定 ID 电影的详细信息

        Args:
            movie_id (str): 电影的唯一标识符

        Returns:
            Optional[Dict]: 如果找到电影，返回包含电影详细信息的字典；否则返回 None
        """
        pass

    @abstractmethod
    def get_all_movie_info(self) -> List[Dict]:
        """
        获取所有电影的信息

        Returns:
            List[Dict]: 包含所有电影信息的字典列表
        """
        pass