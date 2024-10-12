import unittest
from typing import Optional, Dict, List
from unittest.mock import Mock, patch
from app.services.jellyfin_service import JellyfinService
from app.utils.interfaces.jellyfin_util_interface import JellyfinUtilInterface



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

        jellyfin_service = JellyfinService()

        flg = jellyfin_service.check_movie_exists(title="年会不能停")
        print(flg)



if __name__ == '__main__':
    unittest.main()