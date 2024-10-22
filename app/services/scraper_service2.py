from typing import List, Optional
from bs4 import BeautifulSoup

from app.config.app_config import AppConfig
from app.model.db.movie_model import Movie, Chart, ChartEntry, ChartType
from app.utils.download_client import DownloadStatus
from app.services.actor_service import ActorService
from app.services.base_service import BaseService
from app.services.chart_entry_service import ChartEntryService
from app.services.chart_service import ChartService
from app.services.chart_type_service import ChartTypeService
from app.services.download_service import DownloadService
from app.services.movie_service import MovieService
from app.services.studio_service import StudioService
from app.utils.http_util import HttpUtil
from app.utils.page_parser_util import PageParserUtil
from app.config.log_config import debug, info, warning, error, critical
from app.utils.parser.parser_factory import ParserFactory


class ScraperService:
    def __init__(self):
        self.config = AppConfig().get_web_scraper_config()
        self.base_url = self.config.get('javdb_url', "https://javdb.com")
        self.http_util = HttpUtil()
        self.page_parser = PageParserUtil()

        self.actor_service = ActorService()
        self.studio_service = StudioService()
        self.chart_service = ChartService()
        self.chart_type_service = ChartTypeService()
        self.chart_entry_service = ChartEntryService()
        self.movie_service = MovieService()
        self.download_service = DownloadService()

    def process_charts(self):
        """
        处理所有榜单，从本地文件读取电影榜单并爬取信息。
        """

        chart_list = self.chart_service.parse_local_chartlist()
        for chart_from_file in chart_list:
            self._process_chart(chart=chart_from_file)

    def _process_chart(self, chart: Chart):
        """处理单个榜单文件。"""

        # 判断榜单是否存在数据库
        # chart_from_database = self.chart_service.get_by_name_or_create(chart)
        # info(f"{chart.name} 已经存在数据库中，跳过")

        for chart_entry_from_list in chart.entries:

            # 每次都要重新判断 所有内容是否存在，否者可能已经插入

            # 判断chart是否存在数据库。
            chart_from_db = self.chart_service.get_by_name(chart.name)

            if chart_from_db:
                chart = chart_from_db

            # 判断类型是否存在
            default_chart_type = self.chart_type_service.get_current_chart_type()
            chart_type_from_db = self.chart_type_service.get_by_name(default_chart_type.name)

            if chart_type_from_db:
                chart.chart_type = chart_type_from_db
            else:
                chart.chart_type = default_chart_type

            # 通过序列号判断电影是否存在
            movie_from_db = self.movie_service.get_movie_from_db_by_serial_number(chart_entry_from_list.serial_number)

            chart_entry = None
            if movie_from_db and chart_from_db:
                chart_entry_from_db = self.chart_entry_service.get_chart_entry_by_movie_id_and_chart_id(
                    movie_from_db.id, chart_from_db.id)
                if chart_entry_from_db:
                    chart_entry = chart_entry_from_db
                else:
                    chart_entry = chart_entry_from_list
            else:

                chart_entry = chart_entry_from_list

            movie = movie_from_db
            if movie_from_db:
                # 数据库存在这部电影，意味着 演员、导演、系列、制作商、标签、类别等已存在
                pass

            else:

                # 解析电影实体（通过爬虫获得）
                movie_parser = self._get_movie_info_by_chart_entry(chart_entry_from_list)
                movie = movie_parser
                # 数据库不存在电影了，查看判断chart_entry是否存在数据库
                # 导演、演员、等信息应该都存在了
                # 严谨就判断一下

            # 关联
            chart_entry.chart = chart
            chart_entry.movie = movie

            self.chart_entry_service.create(chart_entry_from_list)

            # 电影是否存在
            movie_exists = self.movie_service.exists(chart_entry_from_list.serial_number)

            if movie.have_mg:

                # 那是否有在下载呢
                download_status = self.download_service.get_download_status(chart_entry_from_list.serial_number)

                if download_status and download_status <= DownloadStatus.DOWNLOADING.value:
                    mangnet = movie.mangnet[0]
                    # 没下载或者还在下载中
                    # 如果在下载中，判断下载速度是否超过设定值，如果是，获得下一个磁力。根据电影关联的磁力列表，获得下一个磁力链接。
                    if download_status == DownloadStatus.DOWNLOADING.value:
                        # 电影下载速度
                        fast = self.download_service.check_download_speed(chart_entry_from_list.serial_number)
                        if not fast:
                            mangnet = self.movie_service.get_next_mangnet(chart_entry_from_list.serial_number,
                                                                          movie.mangnet)
                    # 下载电影
                    self.download_service.add_torrent(f"magnet:?xt=urn:btih:{movie.mangnet[0]}")

            # TODO 可在添加缓存在缓存中各种信息，电影的状态
            # 一个电影 在一个榜单只能由一条记录

            # TODO 判断导演、类别、（标签）、系列、演员、制作商、磁力链接在数据库是否存在

    def _get_movie_info_by_chart_entry(self, chart_entry: ChartEntry) -> Optional[dict]:
        """获取电影详细信息。"""
        url = self._get_movie_page_url(chart_entry)
        soup = self.http_util.request(url=url, proxy_enable=self.config["proxy_enable"])

        if soup:
            return self.extract_movie_details_page(soup)

        warning(f"无法获取电影页面: {url}")
        raise ValueError("无法获取电影页面")

    def _get_movie_page_url(self, chart_entry: ChartEntry) -> str:
        """获取电影详情页URL。"""
        if chart_entry.link:
            return chart_entry.link

        # 没有地址要去搜索
        uri = self._search_movie_get_uri(chart_entry.serial_number)
        if uri:
            return f'{self.config["javdb_url"]}{uri}'

        raise ValueError("无法找到电影页面")

    def _search_movie_get_uri(self, serial_number: str) -> Optional[str]:
        """搜索电影并获取URI。"""
        search_url = f'{self.config["javdb_url"]}/search?q={serial_number}&f=all'
        soup = self.http_util.request(url=search_url, proxy_enable=self.config["proxy_enable"])

        if soup:
            return self.extract_movie_page_uri(soup)

        error(f"无法获取搜索页面: {search_url}")
        raise ValueError("无法找到电影页面")

    def extract_movie_page_uri(self, soup: BeautifulSoup):

        # 使用特定解析器
        parser = ParserFactory.get_parser()
        search_result_list = parser.parse_search_results(soup)

        info(search_result_list)

        if search_result_list:
            return search_result_list[0].uri
        else:
            raise ValueError("无法找到匹配的URI")

    def extract_movie_details_page(self, soup):
        """从电影详情页提取电影信息。"""

        # 使用特定解析器
        parser = ParserFactory.get_parser()
        movie_info = parser.parse_movie_details_page(soup)

        return movie_info

    # ------------------use end----------------------

    def _update_database(self, movie_info: dict):
        """更新数据库中的电影信息。"""
        # 更新演员信息

        info(f"已更新数据库中的电影信息: {movie_info['javdb_id']}")

    def _is_movie_in_database(self, movie: Movie) -> bool:
        """检查电影是否在数据库中。"""
        # 实现检查逻辑
        pass

    def _add_movie_to_database(self, movie: Movie):
        """将电影添加到数据库。"""
        # 实现添加逻辑
        pass

    def _is_movie_local(self, movie: Movie) -> bool:
        """检查电影是否在本地存在。"""
        jellyfin_exists = self.jellyfin_service.movie_exists(movie)
        everything_exists = self.everything_service.file_exists(movie.title)
        return jellyfin_exists or everything_exists

    def _get_movie_magnets(self, movie_info: dict) -> List[str]:
        """获取电影的磁力链接。"""
        # 实现获取磁力链接的逻辑
        pass

    def _download_movie(self, movie: Movie, magnets: List[str]):
        """使用qBittorrent下载电影。"""
        for magnet in magnets:
            if self.download_util.download_by_qbittorrent(magnet):
                break
        # 实现下载后的处理逻辑

    def _update_chart_entry_status(self, entry):
        """更新榜单条目的下载状态。"""
        # 实现更新逻辑
        pass
