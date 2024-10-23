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
    """

    CACHE_CONFIG = {
        'movie': ('movie:', 24 * 3600),
        'actor': ('actor:', 24 * 3600),
        'director': ('director:', 24 * 3600),
        'series': ('series:', 24 * 3600),
        'studio': ('studio:', 24 * 3600),
        'genre': ('genre:', 24 * 3600),
        'label': ('label:', 24 * 3600)
    }

    def __init__(self):
        self._initialize_config()
        self._initialize_services()
        self._initialize_utils()

    def _initialize_config(self):
        self.config = AppConfig().get_web_scraper_config()
        self.base_url = self.config.get('javdb_url', "https://javdb.com")

    def _initialize_services(self):
        from app.services import (
            MovieService, ActorService, StudioService, DirectorService,
            GenreService, MagnetService, SeriesService, LabelService,
            ChartService, ChartTypeService, ChartEntryService,
            DownloadService, CacheService, EverythingService,
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
        info(f"处理榜单: {chart.name}")

        # 获取或创建榜单类型
        chart_type = self.chart_type_service.get_current_chart_type()
        db_type = self.chart_type_service.get_by_name(chart_type.name)
        if not db_type:
            db_type = self.chart_type_service.create(chart_type)
        chart.chart_type = db_type

        # 获取或创建榜单
        db_chart = self.chart_service.get_by_name(chart.name)
        if not db_chart:
            db_chart = self.chart_service.create(chart)
        else:
            db_chart.chart_type = db_type
            self.chart_service.update(db_chart)

        # 处理榜单条目
        for entry in chart.entries:
            self._process_chart_entry(entry, db_chart)

    def _process_chart_entry(self, chart_entry: ChartEntry, chart: Chart):
        """处理单个榜单条目"""
        info(f"处理榜单条目: {chart_entry.serial_number}")

        # 解析电影信息
        movie = self._parse_movie(chart_entry.serial_number)
        if not movie:
            info(f"获取电影信息失败: {chart_entry.serial_number}")
            return

        # 处理电影及关联实体
        db_movie = self._process_movie(movie)

        # 创建或更新榜单条目
        chart_entry.chart = chart
        chart_entry.movie = db_movie
        existing_entry = self.chart_entry_service.get_by_chart_and_movie(
            chart.id, db_movie.id)

        if existing_entry:
            existing_entry.rank = chart_entry.rank
            self.chart_entry_service.update(existing_entry)
        else:
            self.chart_entry_service.create(chart_entry)

    def _process_movie(self, movie: Movie) -> Movie:
        """处理电影及其关联实体"""
        # 获取或创建制作商
        if movie.studio:
            db_studio = self._get_or_create_entity(
                movie.studio, self.studio_service)
            movie.studio = db_studio

        # 处理关联实体
        for attr, service in [
            ('actors', self.actor_service),
            ('directors', self.director_service),
            ('series', self.series_service),
            ('genres', self.genre_service),
            ('labels', self.label_service)
        ]:
            if not hasattr(movie, attr):
                continue

            entities = getattr(movie, attr)
            if not entities:
                continue

            db_entities = []
            for entity in entities:
                db_entity = self._get_or_create_entity(entity, service)
                if db_entity:
                    db_entities.append(db_entity)
            setattr(movie, attr, db_entities)

        # 获取或创建电影
        db_movie = self.movie_service.get_movie_from_db_by_serial_number(
            movie.serial_number)

        if db_movie:
            # 更新现有电影信息
            self._update_movie_relations(db_movie, movie)
            self.movie_service.update(db_movie)
            movie = db_movie
        else:
            # 创建新电影
            movie = self.movie_service.create(movie)

        # 处理下载状态
        movie.download_status = self._process_movie_download(movie)
        self.movie_service.update(movie)

        return movie

    def _get_or_create_entity(self, entity: Any, service: BaseService) -> Any:
        """获取或创建实体,并处理缓存"""
        if not entity or not entity.name:
            return None

        # 检查缓存
        cache_type = service.__class__.__name__.lower().replace('service', '')
        cache_key = f"{self.CACHE_CONFIG[cache_type][0]}{entity.name}"

        cached = self.cache_service.get(cache_key)
        if cached:
            return type(entity).from_dict(cached)

        # 查询数据库
        db_entity = service.get_by_name(entity.name)
        if not db_entity:
            db_entity = service.create(entity)

        # 更新缓存
        self.cache_service.set(
            cache_key,
            db_entity.to_dict(),
            self.CACHE_CONFIG[cache_type][1]
        )

        return db_entity

    def _update_movie_relations(self, db_movie: Movie, new_movie: Movie):
        """更新电影关联关系"""
        # 更新基本信息
        for attr in ['name', 'title', 'pic_cover', 'release_date', 'length',
                     'have_mg', 'have_file', 'have_hd', 'have_sub']:
            if hasattr(new_movie, attr):
                setattr(db_movie, attr, getattr(new_movie, attr))

        # 更新关联实体
        if new_movie.studio:
            db_movie.studio = new_movie.studio

        for attr in ['actors', 'directors', 'series', 'genres', 'labels']:
            if hasattr(new_movie, attr):
                new_entities = getattr(new_movie, attr)
                if new_entities:
                    setattr(db_movie, attr, new_entities)

    def _parse_movie(self, serial_number: str) -> Optional[Movie]:
        """解析电影信息"""
        # 获取页面URL
        url = self._get_movie_page_url(serial_number)
        if not url:
            return None

        # 解析电影信息
        soup = self.http_util.request(
            url=url, proxy_enable=self.config['proxy_enable'])
        if not soup:
            return None

        return self.parser.parse_movie_details_page(soup)

    def _get_movie_page_url(self, serial_number: str) -> Optional[str]:
        """获取电影页面URL"""
        search_url = f'{self.base_url}/search?q={serial_number}&f=all'
        soup = self.http_util.request(
            url=search_url, proxy_enable=self.config["proxy_enable"])

        if not soup:
            return None

        results = self.parser.parse_search_results(soup)
        if not results:
            return None

        return f'{self.base_url}{results[0].uri}'

    def _process_movie_download(self, movie: Movie) -> int:
        """处理电影下载状态"""
        if self.jellyfin_service.check_movie_exists(title=movie.serial_number):
            return DownloadStatus.IN_LIBRARY.value
        elif self.everything_service.local_exists_movie(movie.serial_number):
            return DownloadStatus.COMPLETED.value

        if not movie.have_mg or not movie.magnets:
            return DownloadStatus.NO_SOURCE.value

        status = self.download_service.get_download_status(movie.serial_number)
        if status in [DownloadStatus.COMPLETED.value,
                      DownloadStatus.IN_LIBRARY.value]:
            return status

        magnet = movie.magnets[0]
        if self.download_service.add_download(
                f"magnet:?xt=urn:btih:{magnet.magnet_xt}"):
            return DownloadStatus.DOWNLOADING.value

        return DownloadStatus.DOWNLOAD_FAILED.value