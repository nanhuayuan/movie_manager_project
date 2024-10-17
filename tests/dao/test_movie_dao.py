# tests/dao/test_movie_dao.py
import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime

from app.dao.movie_dao import MovieDAO
from app.model.db.movie_model import Movie, Director, Genre, Label, Series, Actor, Studio


class TestMovieDAO(unittest.TestCase):
    """MovieDAO的单元测试类"""

    def setUp(self):
        """测试前的设置"""
        self.movie_dao = MovieDAO()

        # 创建测试用的电影数据
        self.test_movies = [
            Movie(
                id=1,
                title="Test Movie 1",
                censored_id="ABC-123",
                serial_number="123456",
                release_date=datetime(2023, 1, 1),
                have_file=1
            ),
            Movie(
                id=2,
                title="Test Movie 2",
                censored_id="XYZ-789",
                serial_number="789012",
                release_date=datetime(2023, 1, 2),
                have_file=0
            )
        ]

        # 创建测试用的关联数据
        self.test_director = Director(id=1, name="Test Director")
        self.test_genre = Genre(id=1, name="Test Genre")
        self.test_movies[0].directors = [self.test_director]
        self.test_movies[0].genres = [self.test_genre]

    @patch('app.utils.db_util.DBUtil.session_scope')
    def test_get_by_censored_id(self, mock_session_scope):
        """测试通过审查ID获取电影"""
        mock_session = MagicMock()
        mock_session_scope.return_value.__enter__.return_value = mock_session
        mock_session.query.return_value.filter.return_value.first.return_value = self.test_movies[0]

        result = self.movie_dao.get_by_censored_id("ABC-123")

        self.assertEqual(result.censored_id, "ABC-123")
        mock_session.query.assert_called_once_with(Movie)
        mock_session.query.return_value.filter.assert_called_once()

    @patch('app.utils.db_util.DBUtil.session_scope')
    def test_get_by_serial_number(self, mock_session_scope):
        """测试通过序列号获取电影"""
        mock_session = MagicMock()
        mock_session_scope.return_value.__enter__.return_value = mock_session
        mock_session.query.return_value.filter.return_value.first.return_value = self.test_movies[0]

        result = self.movie_dao.get_by_serial_number("123456")

        self.assertEqual(result.serial_number, "123456")
        mock_session.query.assert_called_once_with(Movie)

    @patch('app.utils.db_util.DBUtil.session_scope')
    def test_get_with_relations(self, mock_session_scope):
        """测试获取包含关联信息的电影"""
        mock_session = MagicMock()
        mock_session_scope.return_value.__enter__.return_value = mock_session
        mock_session.query.return_value.options.return_value.filter.return_value.first.return_value = self.test_movies[
            0]

        result = self.movie_dao.get_with_relations(1)

        self.assertEqual(result.id, 1)
        self.assertEqual(len(result.directors), 1)
        self.assertEqual(result.directors[0].name, "Test Director")
        mock_session.query.assert_called_once_with(Movie)

    @patch('app.utils.db_util.DBUtil.session_scope')
    def test_update_download_status(self, mock_session_scope):
        """测试更新下载状态"""
        mock_session = MagicMock()
        mock_session_scope.return_value.__enter__.return_value = mock_session
        mock_session.query.return_value.filter.return_value.first.return_value = self.test_movies[0]

        result = self.movie_dao.update_download_status(1, 1)

        self.assertTrue(result)
        self.assertEqual(self.test_movies[0].have_file, 1)

    @patch('app.utils.db_util.DBUtil.session_scope')
    def test_search_movies(self, mock_session_scope):
        """测试搜索电影"""
        mock_session = MagicMock()
        mock_session_scope.return_value.__enter__.return_value = mock_session
        mock_session.query.return_value.filter.return_value.all.return_value = self.test_movies

        result = self.movie_dao.search_movies("Test")

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0].title, "Test Movie 1")
        mock_session.query.assert_called_once_with(Movie)

    @patch('app.utils.db_util.DBUtil.session_scope')
    def test_get_movies_by_director(self, mock_session_scope):
        """测试获取指定导演的电影"""
        mock_session = MagicMock()
        mock_session_scope.return_value.__enter__.return_value = mock_session
        mock_session.query.return_value.join.return_value.filter.return_value.all.return_value = [self.test_movies[0]]

        result = self.movie_dao.get_movies_by_director(1)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].directors[0].id, 1)
        mock_session.query.assert_called_once_with(Movie)

    @patch('app.utils.db_util.DBUtil.session_scope')
    def test_get_latest_movies(self, mock_session_scope):
        """测试获取最新电影"""
        mock_session = MagicMock()
        mock_session_scope.return_value.__enter__.return_value = mock_session
        mock_session.query.return_value.order_by.return_value.limit.return_value.all.return_value = self.test_movies

        result = self.movie_dao.get_latest_movies(2)

        self.assertEqual(len(result), 2)
        self.assertEqual(result[1].release_date, datetime(2023, 1, 2))
        mock_session.query.assert_called_once_with(Movie)

    def test_singleton(self):
        """测试MovieDAO是否正确实现了单例模式"""
        another_movie_dao = MovieDAO()
        self.assertIs(self.movie_dao, another_movie_dao)


if __name__ == '__main__':
    unittest.main()