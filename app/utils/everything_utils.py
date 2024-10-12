from everytools import EveryTools
from typing import List, Optional
import logging

from app.model.search_types import SearchType
from app.config.config_app import AppConfig


class EverythingUtils:
    """
    用于与 Everything 搜索引擎交互的工具类。
    """

    _instance = None

    def __new__(cls):
        """
        该函数实现单例模式，确保类仅有一个实例。首次调用时：
        1.通过super().__new__(cls)创建实例；
        2.初始化everythingutil，加载everything配置；
        3.从配置中获取everything数据库连接信息；
        4.使用这些信息创建everythingutil对象并存储在类属性_instance.client中。 之后的调用直接返回已有实例。
        """
        if cls._instance is None:
            cls._instance = super().__new__(cls)

            """初始化everythingutil，加载everything配置"""
            config_loader = AppConfig()
            everything_config = config_loader.get_everything_config()

            # 从配置文件中获取数据库连接URL
            everything_url = everything_config.get('host', '127.0.0.1')
            port = everything_config.get('port', 6379)
            exe_path = everything_config.get('exe_path', 'C:/Program Files/Everything/Everything.exe')
            search_timeout_seconds = everything_config.get('search_timeout_seconds', 5)
            search_path = everything_config.get('search_path', '')
            file_extensions = everything_config.get('file_extensions', '')

            # 暂时用不到配置
            cls._instance.es = EveryTools()

        return cls._instance

    def __init__(self):
        """
        初始化 EverythingUtils 类。

        :param config: 包含 Everything 设置的配置字典。
        """
        # self.everything = Everything()
        # self.search_path = config.get('search_path', '')
        # self.file_extensions = config.get('file_extensions', [])
        self.logger = logging.getLogger(__name__)

    def have_movie(self, serial_number: str) -> bool:
        """
        检查本地存储中是否存在电影文件。
        """

        #flg = self.search_movie(serial_number)
        flg = self.search_movie(serial_number)
        if flg is not None:
            return True
        else:
            return False

    def search_movie(self, serial_number: str, search_path='', file_extensions='') -> Optional[str]:
        """
        使用 Everything 搜索电影文件。
        Args:
            serial_number:
            search_type:
            search_path:
            file_extensions:

        Returns:

        """
        try:
            results = self.search(query=serial_number, search_type=SearchType.VIDEO, search_path=search_path,
                                  file_extensions=file_extensions)

            if results is None:
                self.logger.info(f"在本地存储中未找到电影 '{serial_number}'。")
                return None
            else:
                self.logger.info(f"找到电影 '{serial_number}': {results}")
                return results
        except Exception as e:
            self.logger.error(f"搜索 '{serial_number}' 时出错，{str(e)}")
            return None

    def search(self, query: str, search_type: SearchType, search_path='', file_extensions='') -> Optional[str]:
        """
        根据指定的搜索类型执行搜索
        Args:
            query: 要搜索的电影序列号
            search_type: 搜索类型（SearchType 枚举）
            search_path:    搜索路径
            file_extensions: 搜索类型
        return：
            如果找到电影文件，返回完整路径；否则返回 None
        """
        try:
            query = f'"{query}"'
            if len(search_path.strip()):
                query += f' path:"{search_path}"'
            if len(file_extensions.strip()):
                query += f' ext:{"|".join(file_extensions)}'

            if search_type == SearchType.AUDIO:
                self.es.search_audio(query)
            elif search_type == SearchType.ZIP:
                self.es.search_zip(query)
            elif search_type == SearchType.DOC:
                self.es.search_doc(query)
            elif search_type == SearchType.EXE:
                self.es.search_exe(query)
            elif search_type == SearchType.FOLDER:
                self.es.search_folder(query)
            elif search_type == SearchType.PIC:
                self.es.search_pic(query)
            elif search_type == SearchType.VIDEO:
                self.es.search_video(query)
            elif search_type == SearchType.CUSTOM_EXT:
                ext = kwargs.get('ext', '')
                self.es.search_ext(query, ext=ext)
            elif search_type == SearchType.CUSTOM_LOCATION:
                location = kwargs.get('location', '')
                self.es.search_in_located(query, location)
            else:
                self.es.search(query)

            results = self.es.results()
            self.logger.info(f"搜索 '{query}' 完成，类型：{search_type.value}，找到 {len(results)} 个结果。")

            return results
        except Exception as e:
            self.logger.error(f"搜索 '{query}' 时出错，类型：{search_type.value}：{str(e)}")
            return None

    def search_movies(self, movie_titles: List[str]) -> dict:
        """
        使用 Everything 搜索多个电影文件。

        :param movie_titles: 要搜索的电影标题列表。
        :return: 以电影标题为键，文件路径（或 None）为值的字典。
        """
        results = {}
        for title in movie_titles:
            results[title] = self.search_movie(serial_number=title)
        return results

    def check_movie_exists(self, serial_number: str) -> bool:
        """
        检查本地存储中是否存在电影文件。

        :param serial_number: 要检查的电影标题。
        :return: 如果电影存在返回 True，否则返回 False。
        """
        return self.search_movie(serial_number) is not None

    # 使用
    # from app.utils import EverythingUtils
    # from app.config.app_config import AppConfig


