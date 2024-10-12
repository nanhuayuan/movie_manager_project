import unittest
from typing import Optional, Dict, List
from unittest.mock import Mock, patch
from app.services.jellyfin_service import JellyfinService
from app.utils.interfaces.jellyfin_util_interface import JellyfinUtilInterface


class MockJellyfinUtil(JellyfinUtilInterface):
    """
    JellyfinUtilInterface 的模拟实现类

    用于测试目的，实现了接口定义的所有方法。
    actual_implementation 应在测试时被 Mock 对象替换。
    """

    def search_movie(self, title: str) -> Optional[Dict]:
        pass

    def get_movie_details(self, movie_id: str) -> Optional[Dict]:
        pass

    def get_all_movie_info(self) -> List[Dict]:
        pass


class TestJellyfinService(unittest.TestCase):
    """
    JellyfinService 的单元测试类

    测试了 JellyfinService 的所有公共方法，确保它们能够正确处理
    各种情况，包括成功和失败的场景。
    """

    def setUp(self):
        """
        测试前的设置

        创建一个模拟的 JellyfinUtilInterface 实现和 JellyfinService 实例。
        """
        self.mock_util = Mock(spec=JellyfinUtilInterface)
        self.service = JellyfinService(self.mock_util)

    def test_check_movie_exists_true(self):
        """测试检查存在的电影"""
        # 设置模拟对象返回一个存在的电影
        self.mock_util.search_movie.return_value = {"Id": "123", "Name": "Test Movie"}

        result = self.service.check_movie_exists("Test Movie")

        # 验证结果和方法调用
        self.assertTrue(result)
        self.mock_util.search_movie.assert_called_once_with("Test Movie")

    def test_check_movie_exists_false(self):
        """测试检查不存在的电影"""
        # 设置模拟对象返回 None，表示电影不存在
        self.mock_util.search_movie.return_value = None

        result = self.service.check_movie_exists("Nonexistent Movie")

        # 验证结果和方法调用
        self.assertFalse(result)
        self.mock_util.search_movie.assert_called_once_with("Nonexistent Movie")

    def test_get_movie_info_success(self):
        """测试成功获取电影信息"""
        # 设置模拟数据
        movie_data = {"Id": "123", "Name": "Test Movie"}
        movie_details = {"Id": "123", "Name": "Test Movie", "Overview": "Test Overview"}

        # 设置模拟对象的行为
        self.mock_util.search_movie.return_value = movie_data
        self.mock_util.get_movie_details.return_value = movie_details

        result = self.service.get_movie_info("Test Movie")

        # 验证结果和方法调用
        self.assertEqual(result, movie_details)
        self.mock_util.search_movie.assert_called_once_with("Test Movie")
        self.mock_util.get_movie_details.assert_called_once_with("123")

    def test_get_movie_info_not_found(self):
        """测试获取不存在电影的信息"""
        # 设置模拟对象返回 None，表示电影不存在
        self.mock_util.search_movie.return_value = None

        result = self.service.get_movie_info("Nonexistent Movie")

        # 验证结果和方法调用
        self.assertIsNone(result)
        self.mock_util.search_movie.assert_called_once_with("Nonexistent Movie")
        self.mock_util.get_movie_details.assert_not_called()

    def test_get_all_movies_info(self):
        """测试获取所有电影信息"""
        # 设置模拟数据
        mock_movies = [
            {"Id": "123", "Name": "Movie 1"},
            {"Id": "456", "Name": "Movie 2"}
        ]
        self.mock_util.get_all_movie_info.return_value = mock_movies

        result = self.service.get_all_movies_info()

        # 验证结果和方法调用
        self.assertEqual(result, mock_movies)
        self.mock_util.get_all_movie_info.assert_called_once()

    @patch('logging.info')
    def test_logging(self, mock_logging):
        """测试日志记录功能"""
        # 设置模拟数据
        self.mock_util.search_movie.return_value = {"Id": "123"}
        self.mock_util.get_all_movie_info.return_value = [{"Id": "123"}]

        # 测试初始化日志
        JellyfinService(self.mock_util)
        mock_logging.assert_called_with("Jellyfin 服务已初始化")

        # 测试检查电影存在性的日志
        self.service.check_movie_exists("Test Movie")
        mock_logging.assert_called_with("电影 'Test Movie' 存在 于 Jellyfin 库中")

        # 测试获取所有电影信息的日志
        self.service.get_all_movies_info()
        mock_logging.assert_called_with("获取到 1 部电影的信息")


if __name__ == '__main__':
    unittest.main()