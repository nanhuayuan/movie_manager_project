import asyncio
from typing import List, Optional, Dict, Any
from bs4 import BeautifulSoup
from datetime import datetime
from contextlib import contextmanager

from app.config.app_config import AppConfig
from app.model.db.movie_model import Movie, Chart, ChartEntry, ChartType
from app.services.base_service import BaseService
from app.utils.download_client import DownloadStatus
from app.utils.http_util import HttpUtil
from app.utils.page_parser_util import PageParserUtil
from app.utils.parser.parser_factory import ParserFactory
from app.config.log_config import debug, info, error


class ScraperService:
    """电影数据爬取服务

    负责从网页抓取电影信息、处理榜单数据等核心功能。
    实现了缓存机制以提升性能。
    """

    # 缓存配置
    CACHE_CONFIG = {
        'movie': ('movie:', 24 * 3600),  # 24小时
        'actor': ('actor:', 24 * 3600),
        'director': ('director:', 24 * 3600),
        'series': ('series:', 24 * 3600),
        'studio': ('studio:', 24 * 3600),
        'genre': ('genre:', 24 * 3600),
        'label': ('label:', 24 * 3600)
    }

    def __init__(self):
        """初始化配置与服务"""
        self._initialize_config()
        self._initialize_services()
        self._initialize_utils()

    def _initialize_config(self):
        """初始化配置"""
        self.config = AppConfig().get_web_scraper_config()
        self.base_url = self.config.get('javdb_url', "https://javdb.com")

    def _initialize_services(self):
        """初始化所需服务"""
        from app.services import (
            MovieService, ActorService, StudioService, DirectorService,
            GenreService, MagnetService, SeriesService, LabelService,
            ChartService, ChartTypeService, ChartEntryService,
            DownloadService, CacheService,EverythingService,
            JellyfinService
        )

        services = {
            'movie': MovieService,
            'actor': ActorService,
            'studio': StudioService,
            'director': DirectorService,
            'genre': GenreService,
            'magnet': MagnetService,
            'series': SeriesService,
            'label': LabelService,
            'chart': ChartService,
            'chart_type': ChartTypeService,
            'chart_entry': ChartEntryService,
            'download': DownloadService,
            'cache': CacheService,
            'everything': EverythingService,
            'jellyfin': JellyfinService
        }

        for name, service_class in services.items():
            setattr(self, f'{name}_service', service_class())

    def _initialize_utils(self):
        """初始化工具类"""
        self.http_util = HttpUtil()
        self.page_parser = PageParserUtil()
        self.parser = ParserFactory.get_parser()

    def process_charts(self):
        """处理所有榜单数据"""
        info("开始处理榜单数据")
        chart_list = self.chart_service.parse_local_chartlist()

        for chart in chart_list:
            self._process_chart(chart)

        info("榜单处理完成")

    def _process_chart(self, chart: Chart):
        """处理单个榜单及其条目"""
        # 1. 处理榜单类型
        info(f"处理榜单: {chart.name}")
        # 处理榜单类型,每次都要重新获取，处理（第一次会插入）
        chart = self._process_chart_type(chart)
        # 2. 处理榜单条目
        for entry in chart.entries:
            entry.chart = chart
            try:
                self._process_chart_entry(entry)
            except Exception as e:
                error(f"处理榜单条目失败: {str(e)}")
                continue

    def _process_chart_type(self, chart: Chart) -> Chart:
        """处理榜单类型"""
        chart_from_db = self.chart_service.get_by_name(chart.name)
        # 数据库中榜单和类别都存在 直接返回
        if chart_from_db and chart_from_db.chart_type:
            return chart_from_db

        # 榜单存在，意味着榜单类型不存在 更新
        if chart_from_db:
            default_type = self.chart_type_service.get_current_chart_type()
            type_from_db = self.chart_type_service.get_by_name(default_type.name)
            chart_from_db.chart_type = type_from_db or default_type
            return self.chart_service.update(chart_from_db)
        else:
            # 榜单不存在，榜单类型可能存在，创建
            default_type = self.chart_type_service.get_current_chart_type()
            type_from_db = self.chart_type_service.get_by_name(default_type.name)
            chart.chart_type = type_from_db or default_type
            return self.chart_service.create(chart)

    def _process_chart_entry(self, chart_entry: ChartEntry):
        """处理单个榜单条目
        Args:
            chart_entry: 榜单条目实体
        """
        try:
            # 查询电影是否存在
            movie_from_db = self.movie_service.get_movie_from_db_by_serial_number(chart_entry.serial_number)

            # 获取解析的电影信息
            parsed_movie = self._parse_movie(chart_entry.serial_number)
            if not parsed_movie:
                error(f"获取电影信息失败: {chart_entry.serial_number}")
                return
            movie = None
            if movie_from_db:
                # 更新已存在电影的信息
                movie = self._process_movie_info(movie_from_db, parsed_movie)
                debug(f"更新电影信息: {movie.serial_number}")
            else:
                # 创建新电影
                movie = parsed_movie
                movie.download_status = DownloadStatus.CRAWLED.value
                info(f"创建新电影: {movie.serial_number}")

            # 处理关联实体
            self._process_related_entities(movie)

            # 处理下载状态
            parsed_movie.download_status = self._process_movie_download(movie)

            # 更新榜单条目
            chart_entry.movie = movie
            result = self.chart_entry_service.create(chart_entry)

            info(f"榜单条目处理成功: {chart_entry.serial_number}")

        except Exception as e:
            error(f"处理榜单条目失败 {chart_entry.serial_number}: {str(e)}")
            raise

    def _parse_movie(self, serial_number: str) -> Optional[Movie]:
        """解析电影信息
        Args:
            serial_number: 电影番号
        Returns:
            解析后的电影实体
        """
        # 获取页面URL
        url = self._get_movie_page_url(serial_number)
        if not url:
            error(f"获取电影页面URL失败: {serial_number}")
            return None

        # 解析电影信息
        soup = self.http_util.request(url=url)
        if not soup:
            return None

        movie = self.parser.parse_movie_details_page(soup)

        # 检查缓存
        #cache_key = f"movie:{serial_number}"
        #cached_movie = self.cache_service.get(cache_key)
        #if cached_movie:
        #    movie.id = Movie.from_dict(cached_movie).id
        #else:
        # 处理数据库已有记录

            #self.cache_service.set(cache_key, movie.to_dict(), self.CACHE_CONFIG['movie'][1])
        return movie

    def _get_movie_page_url(self, serial_number: str) -> Optional[str]:
        """获取电影页面URL"""
        # 搜索获取URL
        search_url = f'{self.base_url}/search?q={serial_number}&f=all'
        soup = self.http_util.request(url=search_url)

        if not soup:
            return None

        results = self.parser.parse_search_results(soup)
        if not results:
            return None

        return f'{self.base_url}{results[0].uri}'

    def _process_related_entities(self, movie: Movie):
        """处理电影相关实体"""
        entity_mappings = {
            'studio': (self.studio_service, 'studio', False),
            'actors': (self.actor_service, 'actor', True),
            'directors': (self.director_service, 'director', True),
            'series': (self.series_service, 'series', True),
            'genres': (self.genre_service, 'genre', True),
            'labels': (self.label_service, 'label', True)
        }

        for attr, (service, cache_type, is_list) in entity_mappings.items():
            if not hasattr(movie, attr):
                continue

            entities = getattr(movie, attr)
            if not entities:
                continue

            if is_list:
                processed = []
                for entity in entities:
                    processed_entity = self._process_entity(entity, service, cache_type)
            else:
                self._process_entity(entities, service, cache_type)

    def _process_entity(self, entity: Any, service: BaseService, cache_type: str) -> Any:
        """处理单个实体

        Args:
            entity: 实体对象
            service: 实体对应的服务
            cache_type: 缓存类型

        Returns:
            处理后的实体
        """
        if not entity or not entity.name:
            info(f"实体无效: {entity}")
            return None

        # 检查缓存
        cache_key = f"{self.CACHE_CONFIG[cache_type][0]}{entity.name}"
        cached = self.cache_service.get(cache_key)
        if cached:
            # 使用类型(type)来调用classmethod
            entity.id =  type(entity).from_dict(cached).id
        else:
            # 查询数据库
            db_entity = service.get_by_name(entity.name)
            if db_entity:
                self.cache_service.set(cache_key, entity.to_dict(), self.CACHE_CONFIG[cache_type][1])
                entity.id = db_entity.id

        return entity

    def _process_movie_download(self, movie: Movie) -> int:
        """处理电影下载状态"""

        if self.jellyfin_service.check_movie_exists(title=movie.serial_number):
            return DownloadStatus.IN_LIBRARY.value
        elif self.everything_service.local_exists_movie(movie.serial_number):
            return DownloadStatus.COMPLETED.value

        if not movie.have_mg or not movie.magnets:
            return DownloadStatus.NO_SOURCE.value

        status = self.download_service.get_download_status(movie.serial_number)

        # 已完成状态直接返回
        if status in [DownloadStatus.COMPLETED.value, DownloadStatus.IN_LIBRARY.value]:
            return status

        # 添加下载任务
        magnet = movie.magnets[0]
        if self.download_service.add_download(f"magnet:?xt=urn:btih:{magnet.magnet_xt}"):
            return DownloadStatus.DOWNLOADING.value

        return DownloadStatus.DOWNLOAD_FAILED.value


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
        for attr in ['actors', 'directors', 'series', 'studio', 'genres', 'magnets','labels']:
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