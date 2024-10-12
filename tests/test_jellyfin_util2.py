# tests/test_jellyfin_client.py

import unittest
from unittest.mock import Mock, patch
from app.utils.jellyfin_util import JellyfinClientUtility


class TestJellyfinClientUtility(unittest.TestCase):
    """
    测试 JellyfinClientUtility 类的单元测试类。
    """

    def setUp(self):
        """
        在每个测试方法之前运行，用于设置测试环境。
        """
        # 创建一个模拟的 Jellyfin 客户端
        self.mock_client = Mock()
        # 初始化 JellyfinClientUtility 实例
        self.jellyfin_util = JellyfinClientUtility(self.mock_client)

    def test_get_all_movie_info(self):
        """
        测试 get_all_movie_info 方法。
        """
        # 模拟 items_controller.get_items 的返回值
        mock_result = Mock()
        mock_result.items = [{'id': '1', 'name': 'Movie 1'}, {'id': '2', 'name': 'Movie 2'}]
        self.jellyfin_util.items_controller.get_items.return_value = mock_result

        # 调用方法
        result = self.jellyfin_util.get_all_movie_info('user123', 'library456')

        # 验证结果
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['name'], 'Movie 1')
        self.assertEqual(result[1]['name'], 'Movie 2')

        # 验证方法调用
        self.jellyfin_util.items_controller.get_items.assert_called_once_with(
            user_id='user123',
            sort_by="SortName,ProductionYear",
            sort_order='Ascending',
            include_item_types='Movie',
            recursive=True,
            fields='PrimaryImageAspectRatio,MediaSourceCount',
            image_type_limit=1,
            enable_image_types='Primary,Backdrop,Banner,Thumb',
            start_index=0,
            parent_id='library456',
            limit=None
        )

    def test_delete_movie_by_id(self):
        """
        测试 delete_movie_by_id 方法。
        """
        # 调用方法
        result = self.jellyfin_util.delete_movie_by_id('movie789')

        # 验证结果
        self.assertTrue(result)

        # 验证方法调用
        self.jellyfin_util.library_controller.delete_item.assert_called_once_with(item_id='movie789')

    @patch('jellyfin_util.logging.getLogger')
    def test_search_by_fanhao(self, mock_get_logger):
        """
        测试 search_by_fanhao 方法。

        :param mock_get_logger: 模拟的 getLogger 方法
        """
        # 模拟 items_controller.get_items 的返回值
        mock_result = Mock()
        mock_result.items = [Mock(id='movie123')]
        self.jellyfin_util.items_controller.get_items.return_value = mock_result

        # 调用方法
        result = self.jellyfin_util.search_by_fanhao('ABC-123', 'user456')

        # 验证结果
        self.assertEqual(result, 'movie123')

        # 验证日志记录
        mock_logger = mock_get_logger.return_value
        mock_logger.info.assert_any_call("正在搜索番号 'ABC-123'")
        mock_logger.info.assert_any_call("找到匹配番号 'ABC-123' 的电影，ID: movie123")

        # 验证方法调用
        self.jellyfin_util.items_controller.get_items.assert_called_once_with(
            user_id='user456',
            search_term='ABC-123',
            limit=None,
            fields='PrimaryImageAspectRatio,CanDelete,MediaSourceCount',
            recursive=True,
            enable_total_record_count=False,
            image_type_limit=1,
            include_item_types='Movie'
        )


if __name__ == '__main__':
    unittest.main()