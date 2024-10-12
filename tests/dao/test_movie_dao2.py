# test_movie_dao2.py
import unittest

import pytest
from unittest.mock import MagicMock, create_autospec
from app.dao.movie_dao import MovieDAO
from app.model.db.movie_model import Movie


class TestEverythingUtils(unittest.TestCase):
    # 测试用例：通过有效的审查ID获取电影信息
    def test_get_by_censored_id_with_valid_id(self):
        # 创建一个MovieDAO实例，并设置session属性为一个mock对象
        movie_dao = MovieDAO()


        # 设置期望的查询条件和返回结果
        censored_id = '1111'
        expected_movie = Movie(censored_id=censored_id, title='Test Movie')

        # 调用get_by_censored_id方法并验证返回结果
        result = movie_dao.get_by_censored_id(censored_id)
        assert result == expected_movie

    # 测试用例：通过无效的审查ID获取电影信息
    def test_get_by_censored_id_with_invalid_id(self):
        # 创建一个MovieDAO实例，并设置session属性为一个mock对象
        movie_dao = MovieDAO()

        # 设置期望的查询条件和返回结果为None
        censored_id = 'invalid_censored_id'

        # 调用get_by_censored_id方法并验证返回结果
        result = movie_dao.get_by_censored_id(censored_id)
        assert result is None


# 运行pytest时会收集并执行以test_开头的函数
if __name__ == '__main__':
    pytest.main()
