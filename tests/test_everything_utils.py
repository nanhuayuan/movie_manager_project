import unittest
from unittest.mock import patch, MagicMock
from app.utils.everything_utils import EverythingUtils
from app.model.search_types import SearchType


class TestEverythingUtils(unittest.TestCase):

    @patch('app.utils.everything_utils.EveryTools')
    def setUp(self, mock_every_tools):
        """
        测试开始前的设置，为每个测试创建一个 EverythingUtils 实例。
        mock_every_tools: 模拟 EveryTools 类，避免在测试中使用真实的 EveryTools 实例。
        """
        self.utils = EverythingUtils()
        self.mock_every_tools = mock_every_tools.return_value

    def test_singleton(self):
        """
        测试 EverythingUtils 是否正确实现了单例模式。
        """
        utils1 = EverythingUtils()
        utils2 = EverythingUtils()
        self.assertIs(utils1, utils2)

    def test_have_movie_true(self):
        """
        测试 have_movie 方法在电影存在时是否返回 True。
        """
        self.utils.search_movie = MagicMock(return_value="movie_path")
        self.assertTrue(self.utils.have_movie("movie123"))

    def test_have_movie_false(self):
        """
        测试 have_movie 方法在电影不存在时是否返回 False。
        """
        self.utils.search_movie = MagicMock(return_value=None)
        self.assertFalse(self.utils.have_movie("movie456"))

    def test_search_movie_found(self):
        """
        测试 search_movie 方法在找到电影时的行为。
        """
        self.utils.search = MagicMock(return_value="movie_path")
        result = self.utils.search_movie("movie789")
        self.assertEqual(result, "movie_path")
        self.utils.search.assert_called_once_with(
            query="movie789",
            search_type=SearchType.VIDEO,
            search_path='',
            file_extensions=''
        )

    def test_search_movie_not_found(self):
        """
        测试 search_movie 方法在未找到电影时的行为。
        """
        self.utils.search = MagicMock(return_value=None)
        result = self.utils.search_movie("nonexistent_movie")
        self.assertIsNone(result)

    def test_search_movie_exception(self):
        """
        测试 search_movie 方法在发生异常时的行为。
        """
        self.utils.search = MagicMock(side_effect=Exception("Search error"))
        result = self.utils.search_movie("error_movie")
        self.assertIsNone(result)

    def test_search(self):
        """
        测试 search 方法的基本功能。
        """
        self.mock_every_tools.search_video.return_value = None
        self.mock_every_tools.results.return_value = ["movie1", "movie2"]

        result = self.utils.search("DMS", SearchType.VIDEO)

        self.assertEqual(result, ["movie1", "movie2"])
        self.mock_every_tools.search_video.assert_called_once_with('"DMS"')

    def test_search_with_path_and_extensions(self):
        """
        测试 search 方法在指定路径和文件扩展名时的行为。
        """
        self.mock_every_tools.search_video.return_value = None
        self.mock_every_tools.results.return_value = ["movie1"]

        result = self.utils.search("query", SearchType.VIDEO, search_path="/movies", file_extensions="mp4|avi")

        self.assertEqual(result, ["movie1"])
        self.mock_every_tools.search_video.assert_called_once_with('"query" path:"/movies" ext:mp4|avi')

    def test_search_exception(self):
        """
        测试 search 方法在发生异常时的行为。
        """
        self.mock_every_tools.search_video.side_effect = Exception("Search error")

        result = self.utils.search("query", SearchType.VIDEO)

        self.assertIsNone(result)

    def test_search_movies(self):
        """
        测试 search_movies 方法的行为。
        """
        self.utils.search_movie = MagicMock(side_effect=["path1", None, "path3"])
        result = self.utils.search_movies(["movie1", "movie2", "movie3"])

        expected = {"movie1": "path1", "movie2": None, "movie3": "path3"}
        self.assertEqual(result, expected)

    def test_check_movie_exists(self):
        """
        测试 check_movie_exists 方法的行为。
        """
        self.utils.search_movie = MagicMock(side_effect=[None, "path"])

        self.assertFalse(self.utils.check_movie_exists("nonexistent_movie"))
        self.assertTrue(self.utils.check_movie_exists("existing_movie"))


if __name__ == '__main__':
    unittest.main()