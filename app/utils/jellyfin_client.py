from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
import logging
import requests
from jellyfinapi.jellyfinapi_client import JellyfinapiClient
import jellyfin_apiclient_python as jellyfin_apiclient

class BaseJellyfinClient(ABC):
    @abstractmethod
    def search_movie(self, title: str, user_id: Optional[str] = None) -> Optional[dict]:
        pass

    @abstractmethod
    def get_all_movie_info(self, user_id: str = '') -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    def get_movie_details(self, movie_id: str, user_id: str = '') -> Dict[str, Any]:
        pass

    @abstractmethod
    def delete_movie_by_id(self, movie_id: str, user_id: str = '') -> bool:
        pass

    @abstractmethod
    def get_existing_playlists(self, user_id: str = '') -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    def get_playlist_id(self, playlist_name: str, user_id: str = '') -> str:
        pass

    @abstractmethod
    def search_by_serial_number(self, serial_number: str, user_id: str = '') -> List:
        pass

    @abstractmethod
    def add_to_playlist(self, playlist_id: str, ids: str, user_id: str = '') -> bool:
        pass


class JellyfinApiClient(BaseJellyfinClient):
    def __init__(self, api_url: str, api_key: str, user_id: str = '', item_id: str = '', playlists_id: str = ''):
        self.api_url = api_url
        self.api_key = api_key
        self.user_id = user_id
        self.item_id = item_id
        self.playlists_id = playlists_id
        self.client = JellyfinapiClient(x_emby_token=api_key, server_url=api_url)
        self.items_controller = self.client.items
        self.user_library_controller = self.client.user_library
        self.library_controller = self.client.library
        self.playlists_controller = self.client.playlists
        self.logger = logging.getLogger(__name__)

    def _get_user_id(self, user_id: str = '') -> str:
        return user_id or self.user_id

    def search_movie(self, title: str, user_id: Optional[str] = None) -> Optional[dict]:
        user_id = self._get_user_id(user_id)
        try:
            search_result = self.user_library_controller.get_item(user_id, title, include_item_types="Movie")
            return search_result.items[0].to_dict() if search_result and search_result.items else None
        except Exception as e:
            self.logger.error(f"搜索电影 '{title}' 失败: {str(e)}")
            return None

    def get_all_movie_info(self, user_id: str = '') -> List[Dict[str, Any]]:
        user_id = self._get_user_id(user_id)
        result = self.items_controller.get_items(
            user_id=user_id,
            sort_by="SortName,ProductionYear",
            sort_order='Ascending',
            include_item_types='Movie',
            recursive=True,
            fields='PrimaryImageAspectRatio,MediaSourceCount',
            image_type_limit=1,
            parent_id=self.item_id
        )
        return result.items

    def get_movie_details(self, movie_id: str, user_id: str = '') -> Dict[str, Any]:
        user_id = self._get_user_id(user_id)
        return self.user_library_controller.get_item(user_id=user_id, item_id=movie_id)

    def delete_movie_by_id(self, movie_id: str, user_id: str = '') -> bool:
        try:
            self.library_controller.delete_item(item_id=movie_id)
            return True
        except Exception as e:
            self.logger.error(f"删除电影 {movie_id} 失败: {str(e)}")
            return False

    def get_existing_playlists(self, user_id: str = '') -> List[Dict[str, Any]]:
        user_id = self._get_user_id(user_id)
        result = self.items_controller.get_items(
            user_id=user_id,
            sort_by="IsFolder,SortName",
            sort_order='Ascending',
            fields='PrimaryImageAspectRatio,SortName,Path,ChildCount',
            image_type_limit=1,
            parent_id=self.playlists_id
        )
        return result.items

    def get_playlist_id(self, playlist_name: str, user_id: str = '') -> str:
        user_id = self._get_user_id(user_id)
        all_existing_playlists = self.get_existing_playlists(user_id)
        
        for playlist in all_existing_playlists:
            if playlist.name == playlist_name:
                return playlist.id
                
        create_playlist_result = self.playlists_controller.create_playlist(
            name=playlist_name,
            user_id=user_id
        )
        return create_playlist_result.id

    def search_by_serial_number(self, serial_number: str, user_id: str = '') -> List:
        user_id = self._get_user_id(user_id)
        search_result = self.items_controller.get_items(
            user_id=user_id,
            search_term=serial_number,
            recursive=True,
            include_item_types='Movie'
        )
        return search_result.items if search_result.items else None

    def add_to_playlist(self, playlist_id: str, ids: str, user_id: str = '') -> bool:
        user_id = self._get_user_id(user_id)
        try:
            self.playlists_controller.add_to_playlist(
                playlist_id=playlist_id,
                ids=ids,
                user_id=user_id
            )
            return True
        except Exception as e:
            self.logger.error(f"添加到播放列表失败: {str(e)}")
            return False


class JellyfinApiclientPythonClient(BaseJellyfinClient):
    def __init__(self, api_url: str, api_key: str, user_id: str = '', item_id: str = '', playlists_id: str = ''):
        self.api_url = api_url
        self.api_key = api_key
        self.user_id = user_id
        self.item_id = item_id
        self.playlists_id = playlists_id
        self.client = jellyfin_apiclient.JellyfinClient()
        self.client.config.data["auth.server"] = api_url
        self.client.config.data["auth.token"] = api_key
        self.client.auth.config.data["server"] = api_url
        self.client.auth.config.data["token"] = api_key
        self.logger = logging.getLogger(__name__)

    def _get_user_id(self, user_id: str = '') -> str:
        return user_id or self.user_id

    def search_movie(self, title: str, user_id: Optional[str] = None) -> Optional[dict]:
        user_id = self._get_user_id(user_id)
        try:
            params = {
                "SearchTerm": title,
                "IncludeItemTypes": "Movie",
                "Recursive": True
            }
            result = self.client.jellyfin.user_items(user_id, params)
            items = result.get("Items", [])
            return items[0] if items else None
        except Exception as e:
            self.logger.error(f"搜索电影 '{title}' 失败: {str(e)}")
            return None

    def get_all_movie_info(self, user_id: str = '') -> List[Dict[str, Any]]:
        user_id = self._get_user_id(user_id)
        params = {
            "SortBy": "SortName,ProductionYear",
            "SortOrder": "Ascending",
            "IncludeItemTypes": "Movie",
            "Recursive": True,
            "Fields": "PrimaryImageAspectRatio,MediaSourceCount",
            "ImageTypeLimit": 1,
            "ParentId": self.item_id
        }
        result = self.client.jellyfin.user_items(user_id, params)
        return result.get("Items", [])

    def get_movie_details(self, movie_id: str, user_id: str = '') -> Dict[str, Any]:
        user_id = self._get_user_id(user_id)
        return self.client.jellyfin.get_item(user_id, movie_id)

    def delete_movie_by_id(self, movie_id: str, user_id: str = '') -> bool:
        try:
            self.client.jellyfin.delete_item(movie_id)
            return True
        except Exception as e:
            self.logger.error(f"删除电影 {movie_id} 失败: {str(e)}")
            return False

    def get_existing_playlists(self, user_id: str = '') -> List[Dict[str, Any]]:
        user_id = self._get_user_id(user_id)
        params = {
            "SortBy": "IsFolder,SortName",
            "SortOrder": "Ascending",
            "Fields": "PrimaryImageAspectRatio,SortName,Path,ChildCount",
            "ImageTypeLimit": 1,
            "ParentId": self.playlists_id
        }
        result = self.client.jellyfin.user_items(user_id, params)
        return result.get("Items", [])

    def get_playlist_id(self, playlist_name: str, user_id: str = '') -> str:
        user_id = self._get_user_id(user_id)
        all_existing_playlists = self.get_existing_playlists(user_id)
        
        for playlist in all_existing_playlists:
            if playlist["Name"] == playlist_name:
                return playlist["Id"]
                
        result = self.client.jellyfin.create_playlist(playlist_name, user_id)
        return result.get("Id")

    def search_by_serial_number(self, serial_number: str, user_id: str = '') -> List:
        user_id = self._get_user_id(user_id)
        params = {
            "SearchTerm": serial_number,
            "IncludeItemTypes": "Movie",
            "Recursive": True
        }
        result = self.client.jellyfin.user_items(user_id, params)
        items = result.get("Items", [])
        return items if items else None

    def add_to_playlist(self, playlist_id: str, ids: str, user_id: str = '') -> bool:
        user_id = self._get_user_id(user_id)
        try:
            self.client.jellyfin.add_to_playlist(playlist_id, ids, user_id)
            return True
        except Exception as e:
            self.logger.error(f"添加到播放列表失败: {str(e)}")
            return False
