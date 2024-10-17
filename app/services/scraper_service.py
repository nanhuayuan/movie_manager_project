from typing import List, Optional
from bs4 import BeautifulSoup

from app.config.app_config import AppConfig
from app.model.db.movie_model import Movie
from app.services.actor_service import ActorService
from app.services.chart_entry_service import ChartEntryService
from app.services.chart_service import ChartService
from app.services.chart_type_service import ChartTypeService
from app.services.studio_service import StudioService
from app.utils.http_util import HttpUtil
from app.utils.page_parser_util import PageParserUtil
from app.utils.log_util import debug, info, warning, error, critical
from app.utils.parser.parser_factory import ParserFactory


class ScraperService:
    def __init__(self):
        self.config = AppConfig().get_web_scraper_config()
        self.base_url = self.config.get('javdb_url',"https://javdb.com")
        self.http_util = HttpUtil()
        self.page_parser = PageParserUtil()

        self.actor_service = ActorService()
        self.studio_service = StudioService()
        self.chart_service = ChartService()
        self.chart_type_service = ChartTypeService()
        self.chart_entry_service = ChartEntryService()

    def process_charts(self):
        """
        处理所有榜单，从本地文件读取电影榜单并爬取信息。
        """
        chart_type = self.chart_type_service.get_current_chart_type()
        reader = self.chart_service.get_reader(chart_type.chart_file_type)

        md_file_list = reader.read_files()
        info(f"读取了 {len(md_file_list)} 个文件")

        for md_file in md_file_list:
            self._process_chart(md_file)

    def _process_chart(self, md_file):
        """处理单个榜单文件。"""
        chart = self.chart_service.md_file_to_chart(md_file)

        for movie in md_file.movie_info_list:
            movie_info = self._get_movie_info(movie)
            if movie_info:
                self._update_database(movie_info)

            chart_entry = self.chart_entry_service.movie_to_chart_entry(movie=movie)
            chart_entry.movie = movie
            chart.entries.append(chart_entry)

        chart.chart_type = self.chart_type_service.get_current_chart_type()
        success = self.chart_service.create(chart)
        info(f"榜单创建{'成功' if success else '失败'}")

    def _get_movie_info(self, movie: Movie) -> Optional[dict]:
        """获取电影详细信息。"""
        url = self._get_movie_page_url(movie)
        soup = self.http_util.request(url=url, proxy_enable=self.config["proxy_enable"])

        if not soup:
            warning(f"无法获取电影页面: {url}")
            return None

        return self.extract_movie_details_page(soup)

    def _get_movie_page_url(self, movie: Movie) -> str:
        """获取电影详情页URL。"""
        if movie.link:
            return movie.link

        uri = self._search_movie_get_uri(movie.serial_number)
        return f'{self.config["javdb_url"]}/{uri}" if uri else "'

    def _search_movie_get_uri(self, serial_number: str) -> Optional[str]:
        """搜索电影并获取URI。"""
        search_url = f'{self.config["javdb_url"]}/search?q={serial_number}&f=all'
        soup = self.http_util.request(url=search_url, proxy_enable=self.config["proxy_enable"])

        if not soup:
            warning(f"无法获取搜索页面: {search_url}")
            return None

        return self.extract_movie_page_uri(soup)

    def _update_database(self, movie_info: dict):
        """更新数据库中的电影信息。"""
        # 更新演员信息
        for actor_name in movie_info.get('stars', []):
            self.actor_service.update_actor(actor_name, movie_info['javdb_id'])

        # 更新工作室信息
        studio_name = movie_info.get('studio')
        if studio_name:
            self.studio_service.update_studio(studio_name, movie_info['javdb_id'])

        # 更新电影信息
        # 注意：这里假设你有一个 movie_service 来处理电影信息的更新
        # self.movie_service.update_movie(movie_info)

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

    def _get_movie_info(self, movie: Movie) -> dict:
        """获取电影详细信息。"""
        url = self._get_movie_page_url(movie)
        soup = self.http_util.request(url=url, proxy_enable=self.config["proxy_enable"])
        return self._extract_movie_info(soup)

    def _get_movie_page_url(self, movie: Movie) -> str:
        """获取电影详情页URL。"""
        if movie.link:
            return movie.link
        uri = self._search_movie_get_uri(movie.serial_number)
        return f'{self.config["javdb_url"]}{uri}'

    def _search_movie_get_uri(self, serial_number: str) -> str:
        """搜索电影并获取URI。"""
        search_url = f'{self.config["javdb_url"]}/search?q={serial_number}&f=all'
        soup = self.http_util.request(url=search_url, proxy_enable=self.config["proxy_enable"])
        return self._extract_movie_page_uri(soup)

    def _extract_movie_page_uri(self, soup: BeautifulSoup) -> Optional[str]:
        """从搜索结果中提取电影页面URI。"""
        try:
            movie_list = soup.find('div', class_='movie-list')
            first_movie = movie_list.find('a')
            return first_movie['href'] if first_movie else None
        except Exception as e:
            error(f"提取电影页面URI时出错: {str(e)}")
            return None

    def _extract_movie_info(self, soup: BeautifulSoup) -> dict:
        """从电影详情页提取电影信息。"""
        # 实现提取逻辑
        pass

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

    def extract_movie_page_uri(self, soup):

        # 使用特定解析器
        parser = ParserFactory.get_parser()
        search_result_list = parser.parse_search_results(soup)

        info(search_result_list)

        if search_result_list:
            return search_result_list[0].uri
        else:
            raise ValueError("无法找到匹配的URI")

    def extract_movie_details_page(self, soup):
        # 使用特定解析器
        parser = ParserFactory.get_parser()
        movie_info = parser.parse_movie_details_page(soup)

        return movie_info