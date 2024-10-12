import unittest
from unittest.mock import patch, MagicMock
from app.utils.everything_utils import EverythingUtils


class TestEverythingUtils(unittest.TestCase):

    def setUp(self):
        #self.config = {
        #    'search_path': 'D:/Movies',
        #    'file_extensions': ['mp4', 'mkv', 'avi']
        #}
        #self.everything_utils = EverythingUtils(self.config)

        self.everything_utils = EverythingUtils()
        self.everything_utils.search_movie = MagicMock()  # 将earch_movie模拟为MagicMock对象

    #@patch('app.utils.everything_utils.EverythingUtils')
    def test_have_movie_movie_exists(self):
        """
        测试电影存在的情况
        Returns:
        """
        # 设置模拟函数返回值
        self.everything_utils.search_movie.return_value = True
        serial_number = 'DMS'

        # 调用待测函数
        result = self.everything_utils.have_movie(serial_number)

        # 断言，预期返回True
        assert result is True
        self.everything_utils.search_movie.assert_called_once_with(serial_number)  # 确保earch_movie被调用了一次

        # 测试电影不存在的情况

    #@patch('app.utils.everything_utils.EverythingUtils')
    def test_have_movie_movie_not_exists(self):
        """
        测试电影不存在的情况
        Returns:

        """
        # 设置模拟函数返回值为None
        self.everything_utils.search_movie.return_value = None
        serial_number = '大明王朝'

        # 调用待测函数
        result = self.everything_utils.have_movie(serial_number)

        # 断言，预期返回False
        assert result is False
        self.everything_utils.search_movie.assert_called_once_with(serial_number)  # 确保earch_movie被调用了一次

    @patch('app.utils.everything_utils.EverythingUtils')
    def test_search_movie_found(self, mock_everything):
        """
        测试当电影存在时的搜索功能
        Args:
            mock_everything:

        Returns:

        """
        mock_everything().search.return_value = ['D:/Movies/test_movie.mp4']
        result = self.everything_utils.search_movie('test_movie')
        self.assertEqual(result, 'D:/Movies/test_movie.mp4')

    @patch('app.utils.everything_utils.EverythingUtils')
    def test_search_movie_not_found(self, mock_everything):
        """
            测试当电影不存在时的搜索功能
        Args:
            mock_everything:

        Returns:

        """
        mock_everything().search.return_value = []
        result = self.everything_utils.search_movie('nonexistent_movie')
        self.assertIsNone(result)

    @patch('app.utils.everything_utils.EverythingUtils')
    def test_search_movies(self, mock_everything):
        """
            测试批量搜索电影的功能
        Args:
            mock_everything:

        Returns:

        """
        mock_everything().search.side_effect = [
            ['D:/Movies/movie1.mp4'],
            [],
            ['D:/Movies/movie3.avi']
        ]
        results = self.everything_utils.search_movies(['movie1', 'movie2', 'movie3'])
        expected = {
            'movie1': 'D:/Movies/movie1.mp4',
            'movie2': None,
            'movie3': 'D:/Movies/movie3.avi'
        }
        self.assertEqual(results, expected)

    @patch('app.utils.everything_utils.EverythingUtils')
    def test_check_movie_exists(self, mock_everything):
        """
        测试检查电影是否存在的功能
        Args:
            mock_everything:

        Returns:

        """
        mock_everything().search.return_value = ['D:/Movies/existing_movie.mp4']
        self.assertTrue(self.everything_utils.check_movie_exists('existing_movie'))

        mock_everything().search.return_value = []
        self.assertFalse(self.everything_utils.check_movie_exists('nonexistent_movie'))

    @patch('app.utils.everything_utils.EverythingUtils')
    def test_search_movie_with_exception(self, mock_everything):
        """
        测试当发生异常时的错误处理
        Args:
            mock_everything:

        Returns:

        """
        mock_everything().search.side_effect = Exception("Test exception")
        result = self.everything_utils.search_movie('error_movie')
        self.assertIsNone(result)


if __name__ == '__main__':
    unittest.main()
    #pytest.main()

    #测试某个
    #python -m unittest tests.test_everything_utils
    #测试所有
    # python -m unittest discover tests