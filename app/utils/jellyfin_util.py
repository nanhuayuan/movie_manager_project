# app/utils/jellyfin_client.py
from typing import Optional, List, Dict, Any
import logging

from jellyfinapi.jellyfinapi_client import JellyfinapiClient

from app.config.app_config import AppConfig
from app.utils.interfaces.jellyfin_util_interface import JellyfinUtilInterface


class JellyfinUtil(JellyfinUtilInterface):
    """
    Jellyfin API交互工具类

    这个类提供了一个简化的接口，用于执行与Jellyfin服务器的常见操作，
    例如搜索电影、获取电影详情以及检索库中所有电影的列表。
    """
    _instance = None

    def __new__(cls):
        """
        该函数实现单例模式，确保类仅有一个实例。首次调用时：
        1.通过super().__new__(cls)创建实例；
        2.初始化，加载配置；
        3.从配置中获取信息；
        4.使用这些信息创建对象并存储在类属性_instance.client中。 之后的调用直接返回已有实例。
        """
        if cls._instance is None:
            cls._instance = super().__new__(cls)

            """初始化，加载配置"""
            config_loader = AppConfig()
            config = config_loader.get_jellyfin_config()

            # 从配置文件中获取数据库连接URL
            api_url = config.get('api_url', 'http://localhost:8096')
            api_key = config.get('api_key', '')

            # 暂时用不到配置
            cls._instance.client = JellyfinapiClient(
                x_emby_token=api_key,
                server_url=api_url)

        return cls._instance

    def __init__(self):
        """
        初始化Jellyfin客户端工具

        这个方法使用提供的凭证设置Jellyfin客户端，并连接到指定的Jellyfin服务器。

        参数:
            server_url (str): Jellyfin服务器的URL
            api_key (str): 用于认证的API密钥
            device_id (str): 此客户端实例的唯一标识符
            client_name (str): 此客户端应用程序的名称
        """
        """初始化，加载配置"""
        config_loader = AppConfig()
        config = config_loader.get_jellyfin_config()

        server_url = config.get('api_url', 'http://localhost:8096')

        self.user_id = config.get('user_id', '')
        self.item_id = config.get('item_id', '')
        self.playlists_id = config.get('playlists_id', '')

        self.items_controller = self.client.items
        self.item_update_controller = self.client.item_update
        self.user_library_controller = self.client.user_library
        self.library_controller = self.client.library
        self.playlists_controller = self.client.playlists

        # self.client.config.app(deviceName=client_name, deviceId=device_id, version="1.0.0")
        # self.client.config.data["auth.ssl"] = True
        # self.client.config.data["auth.server"] = server_url
        # self.client.config.data["auth.apikey"] = api_key
        # self.client.auth.connect_to_address(server_url)
        # self.client.auth.apikey = api_key
        self.logger = logging.getLogger(__name__)
        logging.info(f"Jellyfin客户端已初始化，服务器地址: {server_url}")

    def _get_default_user_id_and_item_id(self, user_id, item_id) -> Optional[str]:
        """
        获取默认用户的 ID

        返回:
            Optional[str]: 如果成功，返回用户 ID；如果失败，返回 None
        """
        try:
            if ''.__eq__(user_id):
                user_id = self.user_id

            if ''.__eq__(item_id):
                item_id = self.item_id

            return user_id, item_id
        except Exception as e:
            logging.error(f"获取默认用户 ID、item_id 时发生错误: {str(e)}")
            return None

    def search_movie(self, title: str, user_id: Optional[str] = None, item_id: Optional[str] = '', ) -> Optional[dict]:
        """
        通过标题在Jellyfin库中搜索电影 TODO 方法错误

        此方法执行不区分大小写的精确标题匹配搜索。

        参数:
            title (str): 要搜索的电影标题
            user_id (Optional[str]): 要使用的用户 ID。如果为 None，则使用默认用户 ID。
        返回:
            Optional[dict]: 如果找到电影，返回包含电影信息的字典；
                            如果未找到匹配的电影，返回None

        异常:
            Exception: 如果在API调用期间发生错误，将捕获异常，记录日志，并返回None
        """

        user_id, item_id = self._get_default_user_id_and_item_id(user_id, item_id)

        try:
            search_result = self.user_library_controller.get_item(user_id, title, include_item_types="Movie")
            if search_result and search_result.items:
                logging.info(f"找到电影: {title}")
                return search_result.items[0].to_dict()
            logging.info(f"未找到电影: {title}")
            return None
        except Exception as e:
            logging.error(f"搜索电影 '{title}' 时发生错误: {str(e)}")
            return None

    def get_all_movie_info(self, user_id: str = '', item_id: str = '') -> List[Dict[str, Any]]:
        """
        获取指定库中的所有电影信息。

        :param user_id: 用户 ID
        :param item_id: 库 ID
        :return: 包含所有电影信息的列表
        """
        user_id, item_id = self._get_default_user_id_and_item_id(user_id, item_id)
        self.logger.info(f"正在获取用户 {user_id} 的电影库 {item_id} 中的所有电影信息")
        result = self.items_controller.get_items(
            user_id=user_id,
            sort_by="SortName,ProductionYear",
            sort_order='Ascending',
            include_item_types='Movie',
            recursive=True,
            fields='PrimaryImageAspectRatio,MediaSourceCount',
            image_type_limit=1,
            enable_image_types='Primary,Backdrop,Banner,Thumb',
            start_index=0,
            parent_id=item_id,
            limit=None
        )
        self.logger.info(f"成功获取到 {result.total_record_count} 部电影的信息")
        return result.items

    def get_movie_details(self, movie_id: str, user_id: str = '', item_id='') -> Dict[str, Any]:
        """
        获取指定电影的详细信息。

        :param user_id: 用户 ID
        :param movie_id: 电影 ID
        :param item_id: 项目 ID
        :return: 包含电影详细信息的字典

        """
        user_id, item_id = self._get_default_user_id_and_item_id(user_id, item_id)
        self.logger.info(f"正在获取用户 {user_id} 的电影 {movie_id} 的详细信息")
        details = self.user_library_controller.get_item(user_id=user_id, item_id=movie_id)
        self.logger.info(f"成功获取电影 {movie_id} 的详细信息")
        return details

    def delete_movie_by_id(self, movie_id: str) -> bool:
        """
        根据 ID 删除指定的电影。

        :param movie_id: 要删除的电影 ID
        :return: 删除操作是否成功
        """
        self.logger.info(f"正在删除电影 {movie_id}")
        try:
            self.library_controller.delete_item(item_id=movie_id)
            self.logger.info(f"成功删除电影 {movie_id}")
            return True
        except Exception as e:
            self.logger.error(f"删除电影 {movie_id} 时发生错误: {str(e)}")
            return False

    def get_existing_playlists(self, user_id: str = '', parent_id: str = '') -> List[Dict[str, Any]]:
        """
        获取所有已存在的播放列表。

        :param user_id: 用户 ID
        :param parent_id: 父级 ID（通常是播放列表的根目录 ID）
        :return: 包含所有播放列表信息的列表
        """
        user_id, parent_id = self._get_default_user_id_and_item_id(user_id, parent_id)
        self.logger.info(f"正在获取用户 {user_id} 的所有播放列表")
        parent_id = self.playlists_id
        result = self.items_controller.get_items(
            user_id=user_id,
            sort_by="IsFolder,SortName",
            sort_order='Ascending',
            fields='PrimaryImageAspectRatio,SortName,Path,ChildCount,MediaSourceCount,PrimaryImageAspectRatio',
            image_type_limit=1,
            start_index=0,
            parent_id=parent_id,
            limit=None
        )
        self.logger.info(f"成功获取到 {result.total_record_count} 个播放列表")
        return result.items

    def is_existing_playlist(self, playlist_name: str, all_existing_playlists: List[Dict[str, Any]]) -> bool:
        """
        检查指定名称的播放列表是否已存在。

        :param playlist_name: 要检查的播放列表名称
        :param all_existing_playlists: 所有已存在播放列表的列表
        :return: 如果播放列表存在返回 True，否则返回 False
        """
        exists = any(playlist['name'] == playlist_name for playlist in all_existing_playlists)
        self.logger.info(f"播放列表 '{playlist_name}' {'已存在' if exists else '不存在'}")
        return exists

    def get_playlist_id(self, playlist_name: str, all_existing_playlists: List[Dict[str, Any]] = None,
                        user_id: str = '') -> str:
        """
        获取指定播放列表的 ID，如果不存在则创建新的播放列表。

        :param playlist_name: 播放列表名称
        :param all_existing_playlists: 所有已存在播放列表的列表
        :param user_id: 用户 ID
        :return: 播放列表 ID
        """
        if all_existing_playlists == None:
            all_existing_playlists = self.get_existing_playlists(user_id)

        # 检查播放列表是否已存在
        for playlist in all_existing_playlists:
            if playlist.name == playlist_name:
                self.logger.info(f"找到已存在的播放列表 '{playlist_name}', ID: {playlist.id}")
                return playlist.id

        # 如果播放列表不存在，创建新的播放列表
        self.logger.info(f"播放列表 '{playlist_name}' 不存在，正在创建新播放列表")
        create_playlist_result = self.playlists_controller.create_playlist(
            name=playlist_name,
            ids=None,
            user_id=user_id,
            media_type=None,
            body=None
        )
        self.logger.info(f"成功创建新播放列表 '{playlist_name}', ID: {create_playlist_result.id}")
        return create_playlist_result.id

    def get_one_id_by_serial_number_search(self, serial_number: str, user_id: str = '') -> str:

        movie = self.search_one_by_serial_number(serial_number, user_id)
        if movie:
            self.logger.info(f"找到匹配番号 '{serial_number}' 的电影，ID: {movie.id}")
            return movie.id
        else:
            self.logger.warning(f"未找到匹配番号 '{serial_number}' 的电影")
            return None


    def search_one_by_serial_number(self, serial_number: str, user_id: str = '') -> str:

        search_movie_info_list = self.search_by_serial_number(serial_number,user_id)
        if search_movie_info_list:
            self.logger.info(f"找到匹配番号 '{serial_number}' 的电影，ID: {search_movie_info_list[0].id}")
            return search_movie_info_list[0]
        else:
            self.logger.warning(f"未找到匹配番号 '{serial_number}' 的电影")
            return None

    def search_by_serial_number(self, serial_number: str, user_id: str = '') -> List:
        """
        根据番号搜索电影。

        :param fanhao: 要搜索的番号
        :param user_id: 用户 ID
        :return: 如果找到匹配的电影，返回电影 ID；否则返回 None
        """
        user_id, _ = self._get_default_user_id_and_item_id(user_id, item_id='')
        self.logger.info(f"正在搜索番号 '{serial_number}'")

        # 这才是搜索
        # search_result = search_controller.get(user_id=user_id,search_term=fanhao,limit=None,include_people=False,include_media=True,include_genres=False,include_studios=False,include_artists=False,include_item_types='Movie')
        search_result = self.items_controller.get_items(
            user_id=user_id,
            search_term=serial_number,
            limit=None,
            fields='PrimaryImageAspectRatio,CanDelete,MediaSourceCount',
            recursive=True,
            enable_total_record_count=False,
            image_type_limit=1,
            include_item_types='Movie'
        )
        search_movie_info_list = search_result.items
        if search_movie_info_list:
            self.logger.info(f"找到匹配番号 '{serial_number}' 的电影，ID: {search_movie_info_list[0].id}")
            return search_movie_info_list
        else:
            self.logger.warning(f"未找到匹配番号 '{serial_number}' 的电影")
            return None


    def add_to_playlist(self, playlist_id: str, ids: str, user_id: str = '') -> bool:
        """
        将指定的电影添加到播放列表中。

        :param playlist_id: 播放列表 ID
        :param ids: 要添加的电影 ID 或 ID 列表
        :param user_id: 用户 ID
        :return: 添加操作是否成功
        """
        user_id, _ = self._get_default_user_id_and_item_id(user_id, item_id='')
        self.logger.info(f"正在将电影 {ids} 添加到播放列表 {playlist_id}")
        try:
            self.playlists_controller.add_to_playlist(
                playlist_id=playlist_id,
                ids=ids,
                user_id=user_id
            )
            self.logger.info(f"成功将电影 {ids} 添加到播放列表 {playlist_id}")
            return True
        except Exception as e:
            self.logger.error(f"将电影 {ids} 添加到播放列表 {playlist_id} 时发生错误: {str(e)}")
            return False
