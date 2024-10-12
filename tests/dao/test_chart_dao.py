# tests/dao/test_chart_dao.py
import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime

from app.dao.chart_dao import ChartDAO
from app.model.db.movie_model import Chart
from app.utils.db_util import db


class TestChartDAO(unittest.TestCase):
    """ChartDAO的单元测试类"""

    def setUp(self):
        """测试前的设置"""
        self.chart_dao = ChartDAO()
        self.session_mock = MagicMock()

        # 创建一些测试用的图表数据
        self.test_charts = [
            Chart(id=1, name="Test Chart 1", description="Description 1",
                  chart_type="bar", data={"key": "value1"},
                  created_at=datetime(2023, 1, 1)),
            Chart(id=2, name="Test Chart 2", description="Description 2",
                  chart_type="line", data={"key": "value2"},
                  created_at=datetime(2023, 1, 2))
        ]

    @patch('app.utils.db_util.DBUtil.session_scope')
    def test_get_by_name(self, mock_session_scope):
        """测试通过名称获取图表"""
        # 设置模拟的session行为
        mock_session = MagicMock()
        mock_session_scope.return_value.__enter__.return_value = mock_session
        mock_session.query.return_value.filter.return_value.first.return_value = self.test_charts[0]

        # 执行测试
        result = self.chart_dao.get_by_name("Test Chart 1")

        # 验证结果
        self.assertEqual(result.name, "Test Chart 1")
        mock_session.query.assert_called_once_with(Chart)
        mock_session.query.return_value.filter.assert_called_once()

    @patch('app.utils.db_util.DBUtil.session_scope')
    def test_find_by_keyword(self, mock_session_scope):
        """测试通过关键词搜索图表"""
        mock_session = MagicMock()
        mock_session_scope.return_value.__enter__.return_value = mock_session
        mock_session.query.return_value.filter.return_value.all.return_value = self.test_charts

        result = self.chart_dao.find_by_keyword("Test")

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0].name, "Test Chart 1")
        mock_session.query.assert_called_once_with(Chart)

    @patch('app.utils.db_util.DBUtil.session_scope')
    def test_get_recent_charts(self, mock_session_scope):
        """测试获取最近的图表"""
        mock_session = MagicMock()
        mock_session_scope.return_value.__enter__.return_value = mock_session
        mock_session.query.return_value.order_by.return_value.limit.return_value.all.return_value = self.test_charts

        result = self.chart_dao.get_recent_charts(2)

        self.assertEqual(len(result), 2)
        mock_session.query.assert_called_once_with(Chart)
        mock_session.query.return_value.order_by.assert_called_once()
        mock_session.query.return_value.order_by.return_value.limit.assert_called_once_with(2)

    @patch('app.utils.db_util.DBUtil.session_scope')
    def test_update_chart_data(self, mock_session_scope):
        """测试更新图表数据"""
        mock_session = MagicMock()
        mock_session_scope.return_value.__enter__.return_value = mock_session
        mock_session.query.return_value.filter.return_value.first.return_value = self.test_charts[0]

        new_data = {"name": "Updated Chart", "data": {"key": "new_value"}}
        result = self.chart_dao.update_chart_data(1, new_data)

        self.assertEqual(result.name, "Updated Chart")
        self.assertEqual(result.data["key"], "new_value")
        mock_session.flush.assert_called_once()
        mock_session.refresh.assert_called_once_with(result)

    @patch('app.utils.db_util.DBUtil.session_scope')
    def test_get_charts_by_type(self, mock_session_scope):
        """测试通过类型获取图表"""
        mock_session = MagicMock()
        mock_session_scope.return_value.__enter__.return_value = mock_session
        mock_session.query.return_value.filter.return_value.all.return_value = [self.test_charts[0]]

        result = self.chart_dao.get_charts_by_type("bar")

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].chart_type, "bar")
        mock_session.query.assert_called_once_with(Chart)
        mock_session.query.return_value.filter.assert_called_once()

    def test_singleton(self):
        """测试ChartDAO是否正确实现了单例模式"""
        another_chart_dao = ChartDAO()
        self.assertIs(self.chart_dao, another_chart_dao)


if __name__ == '__main__':
    unittest.main()