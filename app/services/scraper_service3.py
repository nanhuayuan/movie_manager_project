from typing import List, Optional
from bs4 import BeautifulSoup

from app.config.app_config import AppConfig
from app.model.db.movie_model import Movie, Chart, ChartEntry, ChartType
from app.model.enums import DownloadStatus
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
from app.utils.log_util import debug, info, warning, error, critical
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
        """处理所有榜单，从本地文件读取电影榜单并爬取信息。"""
        try:
            chart_list = self.chart_service.parse_local_chartlist()
            for chart_from_file in chart_list:
                self._process_chart(chart=chart_from_file)
        except Exception as e:
            error(f"处理榜单时发生错误: {str(e)}")
            raise

    def _process_chart(self, chart: Chart):
        """
        处理单个榜单文件。

        Args:
            chart: Chart对象，包含榜单信息
        """
        try:
            # 1. 处理榜单类型
            chart = self._process_chart_type(chart)

            # 2. 处理榜单条目
            for chart_entry in chart.entries:
                chart_entry.chart = chart
                self._process_chart_entry(chart_entry)

        except Exception as e:
            error(f"处理榜单 {chart.name} 时发生错误: {str(e)}")
            raise

    def _process_chart_type(self, chart: Chart) -> Chart:
        """
        处理榜单类型，并更新榜单信息。

        Args:
            chart: 原始榜单对象

        Returns:
            更新后的榜单对象
        """
        try:
            # 检查榜单是否存在于数据库
            chart_from_db = self.chart_service.get_by_name(chart.name)
            if chart_from_db:
                info(f"榜单 {chart.name} 已存在于数据库中")
                chart.id = chart_from_db.id

            # 获取默认榜单类型
            default_chart_type = self.chart_type_service.get_current_chart_type()
            chart_type_from_db = self.chart_type_service.get_by_name(default_chart_type.name)

            # 更新榜单类型
            chart.chart_type = chart_type_from_db or default_chart_type

            return chart
        except Exception as e:
            error(f"处理榜单类型时发生错误: {str(e)}")
            raise

    def _process_movie_info(self, movie: Movie, parsed_movie: Movie) -> Movie:
        """
        处理电影信息，更新必要的属性。

        Args:
            movie: 数据库中的电影对象
            parsed_movie: 解析得到的电影信息

        Returns:
            更新后的电影对象
        """
        try:
            # 检查并更新电影属性
            for attr in ['actors', 'directors', 'series', 'studio', 'genres', 'magnets']:
                if hasattr(movie, attr) and hasattr(parsed_movie, attr):
                    current_items = getattr(movie, attr)
                    parsed_items = getattr(parsed_movie, attr)

                    # 判断属性是否需要更新
                    needs_update = False

                    # 处理可迭代对象(列表等)
                    if isinstance(current_items, (list, set, tuple)):
                        if isinstance(parsed_items, (list, set, tuple)):
                            # 如果两边都是可迭代对象，比较它们包含的对象的name
                            current_names = {item.name for item in current_items if hasattr(item, 'name')}
                            parsed_names = {item.name for item in parsed_items if hasattr(item, 'name')}
                            needs_update = current_names != parsed_names
                        else:
                            # 类型不匹配，需要更新
                            needs_update = True
                    # 处理单个对象
                    else:
                        if hasattr(current_items, 'name') and hasattr(parsed_items, 'name'):
                            # 如果两边都有name属性，比较name值
                            needs_update = current_items.name != parsed_items.name
                        else:
                            # 如果对象没有name属性，直接比较对象
                            needs_update = current_items != parsed_items

                    if needs_update:
                        debug(f"更新电影 {movie.serial_number} 的 {attr}")
                        setattr(movie, attr, parsed_items)

            return movie
        except Exception as e:
            error(f"处理电影信息时发生错误: {str(e)}")
            raise

    def _process_movie_download(self, movie: Movie):
        """
        处理电影下载相关逻辑。

        Args:
            movie: 电影对象
        """
        try:
            if not movie.have_mg:
                return DownloadStatus.OTHER.value

            download_status = self.download_service.get_download_status(movie.serial_number)
            if not download_status or download_status <= DownloadStatus.DOWNLOADING.value:
                magnet = movie.mangnet[0]

                # 如果正在下载，检查下载速度
                if download_status == DownloadStatus.DOWNLOADING.value:
                    if not self.download_service.check_download_speed(movie.serial_number):
                        magnet = self.download_service.get_next_mangnet(movie.serial_number, movie.mangnet)

                # 添加下载任务
                self.download_service.add_torrent(f"magnet:?xt=urn:btih:{magnet}")
                info(f"已添加电影 {movie.serial_number} 的下载任务")
            return DownloadStatus.DOWNLOADING.value
        except Exception as e:
            error(f"处理电影下载时发生错误: {str(e)}")
            raise

    def _update_existing_chart_entry(self, existing_entry: ChartEntry, new_entry: ChartEntry, updated_movie: Movie):
        """
        更新已存在的榜单条目。

        Args:
            existing_entry: 数据库中已存在的榜单条目
            new_entry: 新的榜单条目信息
            updated_movie: 更新后的电影信息
        """
        try:
            # 更新榜单条目的基本信息（比如排名、评分等）
            existing_entry.rank = new_entry.rank
            existing_entry.score = new_entry.score
            existing_entry.votes = new_entry.votes

            # 如果有其他需要更新的字段，在这里添加

            # 更新关联的电影信息
            existing_entry.movie = updated_movie

            # 保存更新
            self.chart_entry_service.update(existing_entry)
            debug(f"更新榜单条目完成: {existing_entry.serial_number}")

        except Exception as e:
            error(f"更新榜单条目时发生错误: {existing_entry.serial_number} - {str(e)}")
            raise

    def _process_chart_entry(self, chart_entry: ChartEntry):
        """
        处理单个榜单条目。

        Args:
            chart_entry: 榜单条目对象
            chart: 所属榜单对象
        """
        try:
            # 查询电影是否存在
            movie_from_db = self.movie_service.get_movie_from_db_by_serial_number(chart_entry.serial_number)

            # 获取解析的电影信息
            parsed_movie = self._get_movie_info_by_chart_entry(chart_entry)

            if movie_from_db:
                # 更新已存在电影的信息（例如可能存在新增等信息）
                movie = self._process_movie_info(movie_from_db, parsed_movie)
                debug(f"更新电影信息: {movie.serial_number}")
            else:
                # 创建新电影
                movie = parsed_movie
                movie.download_status = DownloadStatus.CRAWLED.value
                info(f"创建新电影: {movie.serial_number}")

            # 处理下载
            # 更新电影状态 TODO
            #movie.download_status =self._process_movie_download(movie)

            # 检查更新电影的演员、导演、系列、制作商、标签、类别等信息 （可能是别的电影存进来的）
            self._check_movie_info_from_db(movie)

            #if not movie_from_db:
                #movie.status = DownloadStatus.DOWNLOADING.value

            # 处理榜单条目
            chart_entry.movie = movie

            # 检查榜单条目是否存在
            if chart_entry.chart.id and movie.id:
                existing_entry = self.chart_entry_service.get_chart_entry_by_movie_id_and_chart_id(
                    movie.id, chart_entry.chart.id)
                if existing_entry:
                    info(f"榜单条目已存在: {chart_entry.serial_number}")
                    #信息有更新（例如磁力链接增加了），那整体也要更新
                    #self._update_existing_chart_entry(existing_entry, chart_entry, movie)
                    # 更新是否恰当？
                    self.chart_entry_service.update(chart_entry)
                    info(f"更新榜单条目: {chart_entry.serial_number}")
                    return

            # 创建新的榜单条目
            self.chart_entry_service.create(chart_entry)
            info(f"创建新的榜单条目: {chart_entry.serial_number}")

        except Exception as e:
            error(f"处理榜单条目时发生错误: {chart_entry.serial_number} - {str(e)}")
            raise

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
        """从搜索结果提取电影页面URI。"""
        parser = ParserFactory.get_parser()
        search_result_list = parser.parse_search_results(soup)

        info(search_result_list)

        if search_result_list:
            return search_result_list[0].uri

        raise ValueError("无法找到匹配的URI")

    def extract_movie_details_page(self, soup):
        """从电影详情页提取电影信息。"""
        parser = ParserFactory.get_parser()
        return parser.parse_movie_details_page(soup)

    def _check_movie_info_from_db(self, movie):
        #从数据库中检查演员、导演、系列、制作商、标签、类别等信息是否存在
        for actor in movie.actors:
            # 不存在id，那就是还没入库，需要判断数据库是否存在
            if not actor.id:
                actor_from_db = self.actor_service.get_actor_by_name(actor.name):
                    if actor_from_db:
                        # TODO 拷贝数据库信息到实体或替换来自数据库（两个都提供）

        # TODO 导演、系列、制作商、标签、类别等信息是否存在，也与actor类似

