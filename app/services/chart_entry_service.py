from dataclasses import dataclass
from typing import Optional

from app.dao import ChartEntryDAO
from app.model.db.movie_model import ChartEntry


# 配置日志记录器

@dataclass
class ChartEntryService:


    def __init__(self):
        self.chart_entry_dao = ChartEntryDAO()


    def get_chart_entry_by_movie_id_and_chart_id_or_create(self, chart_entry: ChartEntry = None) -> Optional[ChartEntry]:
        """
        一个电影只能在一个榜单出现一次
        根据榜单id和电影名称获取榜单条目，如果不存在则创建一个新的
        """

        if not isinstance(chart_entry, ChartEntry):
            raise ValueError("chart_entry must be an instance of ChartEntry")

        try:
            flg = self.chart_entry_dao.get_chart_entry_by_movie_id_and_chart_id(chart_entry)
            if flg is None:
                return self.chart_entry_dao.create(chart_entry)
            else:
                return flg
        except Exception as e:
            # 处理异常
            print(f"An error occurred: {e}")
            return None

