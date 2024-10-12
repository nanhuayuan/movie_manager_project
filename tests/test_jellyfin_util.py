# tests/test_jellyfin_client.py

import unittest
from unittest.mock import Mock, patch
from app.utils.jellyfin_util import JellyfinUtil


class TestJellyfinUtil(unittest.TestCase):
    """
    测试JellyfinUtil类的功能。

    这个测试类覆盖了JellyfinUtil的主要方法，包括初始化、搜索电影、
    获取电影详情、删除电影、获取播放列表等功能。每个测试方法都模拟了
    Jellyfin API的响应，以确保JellyfinUtil正确处理各种情况。
    """

    def setUp(self):
        """
        在每个测试方法之前运行，设置测试环境。
        """
        # 模拟配置加载器
        self.mock_config_loader = Mock()
        self.mock_config_loader.get_jellyfin_config.return_value = {
            'api_url': 'http://localhost:8096',
            'api_key': '1d4f983cf0a04522a444965fdfbfde9e',
            'user_id': '5207a4b5a7bf4167ae81ba9d5f341c74',
            'item_id': '3227ce1e069754c594af25ea66d69fc7',
            'playlists_id': '953141ca3d64b4e0bf3ff52b29bcbbab'
        }

        # 使用补丁替换真实的ConfigLoader
        self.patcher = patch('app.utils.jellyfin_util.ConfigLoader', return_value=self.mock_config_loader)
        self.patcher.start()

        # 初始化JellyfinUtil实例
        self.jellyfin_util = JellyfinUtil()

    def tearDown(self):
        """
        在每个测试方法之后运行，清理测试环境。
        """
        self.patcher.stop()

    def test_singleton_instance(self):
        """
        测试JellyfinUtil的单例模式是否正确实现。
        """
        instance1 = JellyfinUtil()
        instance2 = JellyfinUtil()
        self.assertIs(instance1, instance2, "单例模式未正确实现")

    @patch('app.utils.jellyfin_util.JellyfinapiClient')
    def test_search_movie(self, mock_jellyfin_client):
        """
        测试search_movie方法是否正确搜索电影。
        """
        # 模拟API响应
        mock_response = Mock()
        mock_response.items = [{'title': 'Test Movie', 'id': 'test_movie_id'}]
        mock_jellyfin_client.return_value.user_library.get_item_by_name.return_value = mock_response

        result = self.jellyfin_util.search_movie('Test Movie')
        self.assertIsNotNone(result, "搜索电影应返回结果")
        self.assertEqual(result['title'], 'Test Movie', "搜索结果应匹配预期电影")

    @patch('app.utils.jellyfin_util.JellyfinapiClient')
    def test_get_all_movie_info(self, mock_jellyfin_client):
        """
        测试get_all_movie_info方法是否正确获取所有电影信息。
        """
        # 模拟API响应
        mock_response = Mock()
        mock_response.items = [{'title': 'Movie 1'}, {'title': 'Movie 2'}]
        mock_response.result.total_record_count = 2
        mock_jellyfin_client.return_value.items.get_items.return_value = mock_response

        result = self.jellyfin_util.get_all_movie_info('test_user_id', 'test_item_id')
        self.assertEqual(len(result), 2, "应返回正确数量的电影")
        self.assertEqual(result[0]['title'], 'Movie 1', "电影信息应正确匹配")

    @patch('app.utils.jellyfin_util.JellyfinapiClient')
    def test_get_movie_details(self, mock_jellyfin_client):
        """
        测试get_movie_details方法是否正确获取电影详情。
        """
        # 模拟API响应
        mock_response = {'title': 'Test Movie', 'description': 'Test Description'}
        mock_jellyfin_client.return_value.user_library.get_item.return_value = mock_response

        result = self.jellyfin_util.get_movie_details('test_user_id', 'test_movie_id')
        self.assertEqual(result['title'], 'Test Movie', "电影详情应正确匹配")
        self.assertEqual(result['description'], 'Test Description', "电影描述应正确匹配")

    @patch('app.utils.jellyfin_util.JellyfinapiClient')
    def test_delete_movie_by_id(self, mock_jellyfin_client):
        """
        测试delete_movie_by_id方法是否正确删除电影。
        """
        mock_jellyfin_client.return_value.library.delete_item.return_value = None

        result = self.jellyfin_util.delete_movie_by_id('test_movie_id')
        self.assertTrue(result, "删除电影应返回True")

    @patch('app.utils.jellyfin_util.JellyfinapiClient')
    def test_get_existing_playlists(self, mock_jellyfin_client):
        """
        测试get_existing_playlists方法是否正确获取现有播放列表。
        """
        # 模拟API响应
        mock_response = Mock()
        mock_response.items = [{'name': 'Playlist 1'}, {'name': 'Playlist 2'}]
        mock_response.total_record_count = 2
        mock_jellyfin_client.return_value.items.get_items.return_value = mock_response

        result = self.jellyfin_util.get_existing_playlists('test_user_id')
        self.assertEqual(len(result), 2, "应返回正确数量的播放列表")
        self.assertEqual(result[0]['name'], 'Playlist 1', "播放列表信息应正确匹配")

    def test_is_existing_playlist(self):
        """
        测试is_existing_playlist方法是否正确检查播放列表是否存在。
        """
        existing_playlists = [{'name': 'Playlist 1'}, {'name': 'Playlist 2'}]
        self.assertTrue(self.jellyfin_util.is_existing_playlist('Playlist 1', existing_playlists))
        self.assertFalse(self.jellyfin_util.is_existing_playlist('Playlist 3', existing_playlists))

    @patch('app.utils.jellyfin_util.JellyfinapiClient')
    def test_get_playlist_id(self, mock_jellyfin_client):
        """
        测试get_playlist_id方法是否正确获取或创建播放列表ID。
        """
        existing_playlists = [{'name': 'Playlist 1', 'id': 'playlist_1_id'}]

        # 测试获取现有播放列表ID
        result = self.jellyfin_util.get_playlist_id('Playlist 1', existing_playlists, 'test_user_id')
        self.assertEqual(result, 'playlist_1_id', "应返回现有播放列表的ID")

        # 测试创建新播放列表
        mock_create_response = Mock()
        mock_create_response.id = 'new_playlist_id'
        mock_jellyfin_client.return_value.playlists.create_playlist.return_value = mock_create_response

        result = self.jellyfin_util.get_playlist_id('New Playlist', existing_playlists, 'test_user_id')
        self.assertEqual(result, 'new_playlist_id', "应返回新创建的播放列表ID")

    @patch('app.utils.jellyfin_util.JellyfinapiClient')
    def test_search_by_serial_number(self, mock_jellyfin_client):
        """
        测试search_by_serial_number方法是否正确搜索电影。
        """
        # 模拟API响应
        mock_response = Mock()
        mock_response.items = [Mock(id='test_movie_id')]
        mock_jellyfin_client.return_value.items.get_items.return_value = mock_response

        result = self.jellyfin_util.search_by_serial_number('SN001', 'test_user_id')
        self.assertEqual(result, 'test_movie_id', "应返回匹配的电影ID")

    @patch('app.utils.jellyfin_util.JellyfinapiClient')
    def test_add_to_playlist(self, mock_jellyfin_client):
        """
        测试add_to_playlist方法是否正确将电影添加到播放列表。
        """
        mock_jellyfin_client.return_value.playlists.add_to_playlist.return_value = None

        result = self.jellyfin_util.add_to_playlist('test_playlist_id', 'test_movie_id', 'test_user_id')
        self.assertTrue(result, "添加电影到播放列表应返回True")


if __name__ == '__main__':
    unittest.main()
