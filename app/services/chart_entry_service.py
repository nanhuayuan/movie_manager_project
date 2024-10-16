from dataclasses import dataclass
from typing import Optional

from app.dao import ChartEntryDAO
from app.model.db.movie_model import ChartEntry, Movie
from app.model.enums import DownloadStatus
from app.utils.log_util import debug, info, warning, error, critical


@dataclass
class ChartEntryService:
    def __init__(self):
        self.chart_entry_dao = ChartEntryDAO()
        info("ChartEntryService initialized")

    def get_chart_entry_by_movie_id_and_chart_id_or_create(self, chart_entry: ChartEntry = None) -> Optional[
        ChartEntry]:
        """
        获取或创建榜单条目。

        一个电影只能在一个榜单出现一次。
        根据榜单id和电影名称获取榜单条目，如果不存在则创建一个新的。

        Args:
            chart_entry (ChartEntry): 要获取或创建的榜单条目对象

        Returns:
            Optional[ChartEntry]: 获取到的或新创建的榜单条目，如果出现错误则返回None
        """
        if not isinstance(chart_entry, ChartEntry):
            error("Invalid input: chart_entry must be an instance of ChartEntry")
            raise ValueError("chart_entry must be an instance of ChartEntry")

        try:
            debug(
                f"Attempting to get chart entry for movie_id: {chart_entry.movie_id} and chart_id: {chart_entry.chart_id}")
            existing_entry = self.chart_entry_dao.get_chart_entry_by_movie_id_and_chart_id(chart_entry)

            if existing_entry is None:
                info(
                    f"Chart entry not found. Creating new entry for movie_id: {chart_entry.movie_id} and chart_id: {chart_entry.chart_id}")
                return self.chart_entry_dao.create(chart_entry)
            else:
                info(
                    f"Existing chart entry found for movie_id: {chart_entry.movie_id} and chart_id: {chart_entry.chart_id}")
                return existing_entry
        except Exception as e:
            error(f"An error occurred while processing chart entry: {e}")
            return None

    def movie_to_chart_entry(self, movie: Movie) -> ChartEntry:
        """将 Movie 对象转换为 ChartEntry 对象"""
        debug(f"Converting Movie to ChartEntry: {movie.title}")
        return ChartEntry(
            rank=movie.rank,
            status=DownloadStatus.NOT_CRAWLED.value
        )