import unittest
from unittest.mock import MagicMock, patch
from app.services.chart_service import ChartService
from app.model.chart_file_type_enun import ChartFileType
from app.model.db.movie_model import ChartType

class TestChartService(unittest.TestCase):

    def setUp(self):
        # 假设的初始化操作，可以根据实际情况添加
        self.chart_service = ChartService()


    def test_get_movie_chart_and_chary_type_default(self):
        # 测试默认参数情况
        charts, chart_type = self.chart_service.get_movie_chart_and_chary_type()

        flg = self.chart_service.save_chart_data_to_db_and_cache(md_file_list=charts, chart_type=chart_type)

        print(flg)



if __name__ == '__main__':
    unittest.main()
