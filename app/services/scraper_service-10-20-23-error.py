from typing import List, Optional, Dict, Any
from bs4 import BeautifulSoup
import traceback
from datetime import datetime
import json

from app.config.app_config import AppConfig
from app.model.db.movie_model import Movie, Chart, ChartEntry, ChartType
from app.model.enums import DownloadStatus
from app.services.actor_service import ActorService
from app.services.base_service import BaseService
from app.services.chart_entry_service import ChartEntryService
from app.services.chart_service import ChartService
from app.services.chart_type_service import ChartTypeService
from app.services.director_service import DirectorService
from app.services.download_service import DownloadService
from app.services.genre_service import GenreService
from app.services.label_service import LabelService
from app.services.magnet_service import MagnetService
from app.services.movie_service import MovieService
from app.services.series_service import SeriesService
from app.services.studio_service import StudioService
from app.services.cache_service import CacheService
from app.utils.http_util import HttpUtil
from app.utils.page_parser_util import PageParserUtil
from app.config.log_config import debug, info, warning, error, critical
from app.utils.parser.parser_factory import ParserFactory
from app.utils.retry_util import RetryUtil


class ScraperService:
    # Redis缓存键前缀
    CACHE_KEY_MOVIE = "movie:"
    CACHE_KEY_ACTOR = "actor:"
    CACHE_KEY_DIRECTOR = "director:"
    CACHE_KEY_SERIES = "series:"
    CACHE_KEY_STUDIO = "studio:"
    CACHE_KEY_GENRE = "genre:"
    CACHE_KEY_LABEL = "label:"
    CACHE_EXPIRE_TIME = 3600 * 24  # 24小时

    def __init__(self):
        self.config = AppConfig().get_web_scraper_config()
        self.base_url = self.config.get('javdb_url', "https://javdb.com")

        self.movie_service = MovieService()  # 电影
        self.actor_service = ActorService()  # 演员
        self.studio_service = StudioService()  # 制作商
        self.director_service = DirectorService()  # 导演
        self.genre_service = GenreService()  # 类别
        self.magnet_service = MagnetService()  # 类别
        self.series_service = SeriesService()  # 系列
        self.label_service = LabelService()  # 系列

        self.chart_service = ChartService()
        self.chart_type_service = ChartTypeService()
        self.chart_entry_service = ChartEntryService()

        self.http_util = HttpUtil()
        self.page_parser = PageParserUtil()
        self.download_service = DownloadService()
        self.cache_service = CacheService()

        # 记录处理失败的条目
        self.failed_entries = []

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

    def _save_failed_entries(self):
        """保存处理失败的条目到文件"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"failed_entries_{timestamp}.json"
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(self.failed_entries, f, ensure_ascii=False, indent=2)
            info(f"已保存失败记录到文件: {filename}")
        except Exception as e:
            error(f"保存失败记录时出错: {str(e)}")

    def _check_and_update_entity_info(self, entity_list: List[Any], service: Any, cache_key_prefix: str) -> List[Any]:
        """检查并更新实体信息（演员、导演等）

        Args:
            entity_list: 实体列表
            service: 对应的服务类实例
            cache_key_prefix: 缓存键前缀

        Returns:
            更新后的实体列表
        """
        updated_list = []
        for entity in entity_list:
            if not entity.id:
                # 先查缓存
                cache_key = f"{cache_key_prefix}{entity.name}"
                cached_entity = self.cache_service.get(cache_key)

                if cached_entity:
                    entity = cached_entity
                else:
                    # 查询数据库
                    db_entity = service.get_by_name(entity.name)
                    if db_entity:
                        # 合并新旧信息
                        for attr, value in vars(entity).items():
                            if value and not getattr(db_entity, attr):
                                setattr(db_entity, attr, value)
                        entity = db_entity
                    else:
                        # 新建实体
                        entity = service.create(entity)

                    # 更新缓存
                    self.cache_service.set(cache_key, entity.to_dict(), self.CACHE_EXPIRE_TIME)

            updated_list.append(entity)
        return updated_list

    def _check_movie_info_from_db(self, movie: Movie):
        """检查并更新电影相关信息"""
        # 从数据库中检查演员、导演、系列、制作商、标签、类别等信息是否存在
        # 更新演员信息
        movie.actors = self._check_and_update_entity_info(
            movie.actors, self.actor_service, self.CACHE_KEY_ACTOR
        )

        # 更新导演信息
        movie.directors = self._check_and_update_entity_info(
            movie.directors, self.director_service, self.CACHE_KEY_DIRECTOR
        )

        # 更新系列信息
        movie.series = self._check_and_update_entity_info(
            movie.series, self.series_service, self.CACHE_KEY_SERIES
        )

        # 更新制作商信息
        if movie.studio and not movie.studio.id:
            cache_key = f"{self.CACHE_KEY_STUDIO}{movie.studio.name}"
            cached_studio = self.cache_service.get(cache_key)

            if cached_studio:
                movie.studio = cached_studio
            else:
                db_studio = self.studio_service.get_by_name(movie.studio.name)
                if db_studio:
                    movie.studio = db_studio
                else:
                    movie.studio = self.studio_service.create(movie.studio)
                self.cache_service.set(cache_key, movie.studio.to_dict(), self.CACHE_EXPIRE_TIME)

        # 更新标签信息
        movie.labels = self._check_and_update_entity_info(
            movie.labels, self.label_service, self.CACHE_KEY_LABEL
        )

        # 更新类别信息
        movie.genres = self._check_and_update_entity_info(
            movie.genres, self.genre_service, self.CACHE_KEY_GENRE
        )

    #@RetryUtil.retry_on_exception(max_attempts=3, delay=2.0)
    def _get_movie_info_by_chart_entry(self, chart_entry: ChartEntry) -> Optional[Movie]:
        """获取电影详细信息，支持重试"""
        cache_key = f"{self.CACHE_KEY_MOVIE}{chart_entry.serial_number}"
        cached_movie = self.cache_service.get(cache_key)

        if cached_movie:
            return Movie.from_dict(cached_movie)

        url = self._get_movie_page_url(chart_entry)
        soup = self.http_util.request(url=url, proxy_enable=self.config["proxy_enable"])

        if soup:
            movie = self.extract_movie_details_page(soup)
            if movie:
                self.cache_service.set(cache_key, movie.to_dict(), self.CACHE_EXPIRE_TIME)
                return movie

        warning(f"无法获取电影页面: {url}")
        raise ValueError("无法获取电影页面")

    def _process_movie_download(self, movie: Movie) -> int:
        """处理电影下载相关逻辑"""
        try:
            if not movie.have_mg:
                return DownloadStatus.OTHER.value

            download_status = self.download_service.get_download_status(movie.serial_number)

            # 如果已经完成下载，直接返回状态
            if download_status in [DownloadStatus.COMPLETED.value, DownloadStatus.IN_LIBRARY.value]:
                return download_status

            if not download_status or download_status <= DownloadStatus.DOWNLOADING.value:
                if not movie.magnets:
                    warning(f"电影 {movie.serial_number} 没有可用的磁力链接")
                    return DownloadStatus.NO_SOURCE.value

                magnet = movie.magnets[0]

                # 如果正在下载，检查下载速度
                if download_status == DownloadStatus.DOWNLOADING.value:
                    if not self.download_service.check_download_speed(movie.serial_number):
                        magnet = self.download_service.get_next_magnet(movie.serial_number, movie.magnets)

                # 添加下载任务
                success = self.download_service.add_torrent(f"magnet:?xt=urn:btih:{magnet.hash}")
                if success:
                    info(f"已添加电影 {movie.serial_number} 的下载任务")
                    return DownloadStatus.DOWNLOADING.value
                else:
                    warning(f"添加下载任务失败: {movie.serial_number}")
                    return DownloadStatus.DOWNLOAD_FAILED.value

            return download_status

        except Exception as e:
            error(f"处理电影下载时发生错误: {str(e)}")
            return DownloadStatus.DOWNLOAD_FAILED.value

    def _process_chart_entry(self, chart_entry: ChartEntry):
        """处理单个榜单条目"""
        try:
            # 查询电影是否存在
            movie_from_db = self.movie_service.get_movie_from_db_by_serial_number(chart_entry.serial_number)

            # 获取解析的电影信息
            parsed_movie = self._get_movie_info_by_chart_entry(chart_entry)

            if movie_from_db:
                # 更新已存在电影的信息
                movie = self._process_movie_info(movie_from_db, parsed_movie)
                debug(f"更新电影信息: {movie.serial_number}")
            else:
                # 创建新电影
                movie = parsed_movie
                movie.download_status = DownloadStatus.CRAWLED.value
                info(f"创建新电影: {movie.serial_number}")

            # 检查更新电影的关联信息
            self._check_movie_info_from_db(movie)

            # 处理下载
            movie.download_status = self._process_movie_download(movie)

            # 处理榜单条目
            chart_entry.movie = movie

            # 检查榜单条目是否存在
            if chart_entry.chart.id and movie.id:
                existing_entry = self.chart_entry_service.get_chart_entry_by_movie_id_and_chart_id(
                    movie.id, chart_entry.chart.id)
                if existing_entry:
                    debug(f"更新榜单条目: {chart_entry.serial_number}")
                    self._update_existing_chart_entry(existing_entry, chart_entry, movie)
                    return

            # 创建新的榜单条目
            self.chart_entry_service.create(chart_entry)
            info(f"创建新的榜单条目: {chart_entry.serial_number}")

        except Exception as e:
            error(f"处理榜单条目时发生错误: {chart_entry.serial_number} - {str(e)}")
            self.failed_entries.append({
                'serial_number': chart_entry.serial_number,
                'chart_name': chart_entry.chart.name,
                'error': str(e),
                'traceback': traceback.format_exc()
            })
            raise
