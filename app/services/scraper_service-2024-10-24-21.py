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
        # 添加实体缓存，避免同一批次重复查询
        self._entity_cache = {}

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
        # 清空实体缓存
        self._entity_cache = {}

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
    def _get_cached_entity(self, entity_type: str, name: str) -> Optional[Any]:
        """从内存缓存获取实体"""
        cache_key = f"{entity_type}:{name}"
        return self._entity_cache.get(cache_key)

    def _set_cached_entity(self, entity_type: str, name: str, entity: Any):
        """设置内存缓存实体"""
        cache_key = f"{entity_type}:{name}"
        self._entity_cache[cache_key] = entity

    def _get_or_create_entity(self, entity: Any, service: BaseService) -> Any:
        """获取或创建实体,并处理缓存
        优化: 增加内存缓存，解决同一批次的重复查询问题
        """
        if not entity or not entity.name:
            return None

        # 获取实体类型
        entity_type = service.__class__.__name__.lower().replace('service', '')

        # 1. 检查内存缓存
        cached_entity = self._get_cached_entity(entity_type, entity.name)
        if cached_entity:
            return cached_entity

        # 2. 检查Redis缓存
        cache_key = f"{self.CACHE_CONFIG[entity_type][0]}{entity.name}"
        cached = self.cache_service.get(cache_key)
        if cached:
            entity_obj = type(entity).from_dict(cached)
            self._set_cached_entity(entity_type, entity.name, entity_obj)
            return entity_obj

        # 3. 查询数据库
        db_entity = service.get_by_name(entity.name)
        if db_entity:
            # 更新缓存
            self._set_cached_entity(entity_type, entity.name, db_entity)
            self.cache_service.set(
                cache_key,
                db_entity.to_dict(),
                self.CACHE_CONFIG[entity_type][1]
            )
            return db_entity

        # 4. 创建新实体
        new_entity = service.create(entity)
        self._set_cached_entity(entity_type, entity.name, new_entity)
        self.cache_service.set(
            cache_key,
            new_entity.to_dict(),
            self.CACHE_CONFIG[entity_type][1]
        )
        return new_entity

    def _process_movie(self, movie: Movie) -> Movie:
        """处理电影及其关联实体"""
        # 获取或创建制作商
        if movie.studio:
            db_studio = self._get_or_create_entity(
                movie.studio, self.studio_service)
            movie.studio = db_studio

        # 处理关联实体
        entity_services = [
            ('actors', self.actor_service),
            ('directors', self.director_service),
            ('series', self.series_service),
            ('genres', self.genre_service),
            ('labels', self.label_service)
        ]

        for attr, service in entity_services:
            if not hasattr(movie, attr):
                continue

            entities = getattr(movie, attr)
            if not entities:
                continue

            # 获取或创建关联实体
            db_entities = []
            for entity in entities:
                db_entity = self._get_or_create_entity(entity, service)
                if db_entity:
                    db_entities.append(db_entity)

            # 设置关联
            setattr(movie, attr, db_entities)

        # 获取或更新电影
        db_movie = self.movie_service.get_movie_from_db_by_serial_number(
            movie.serial_number)

        if db_movie:
            # 更新现有电影
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

    def _update_movie_relations(self, db_movie: Movie, new_movie: Movie):
        """更新电影关联关系，保持已有关联"""
        # 更新基本信息
        for attr in ['name', 'title', 'pic_cover', 'release_date', 'length',
                     'have_mg', 'have_file', 'have_hd', 'have_sub']:
            if hasattr(new_movie, attr):
                setattr(db_movie, attr, getattr(new_movie, attr))

        # 更新制作商
        if new_movie.studio:
            db_movie.studio = new_movie.studio

        # 更新多对多关联
        relation_attrs = ['actors', 'directors', 'series', 'genres', 'labels']
        for attr in relation_attrs:
            if not hasattr(new_movie, attr):
                continue

            new_entities = getattr(new_movie, attr)
            if not new_entities:
                continue

            # 获取现有关联
            existing_entities = getattr(db_movie, attr)
            existing_names = {e.name for e in existing_entities}

            # 添加新的关联
            for entity in new_entities:
                if entity.name not in existing_names:
                    existing_entities.append(entity)

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

        # 查找已存在的榜单条目
        existing_entry = self.chart_entry_service.get_by_chart_and_movie(
            chart.id, db_movie.id)

        if existing_entry:
            existing_entry.rank = chart_entry.rank
            self.chart_entry_service.update(existing_entry)
        else:
            self.chart_entry_service.create(chart_entry)

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