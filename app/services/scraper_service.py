import asyncio
from typing import List, Optional, Dict, Any
from datetime import datetime

from app.config.app_config import AppConfig
from app.model.db.movie_model import Movie, Chart, ChartEntry, ChartType, db
from app.services.base_service import BaseService
from app.utils.http_util import HttpUtil
from app.utils.parser.parser_factory import ParserFactory
from app.config.log_config import debug, info, error


class ScraperService:
    """电影数据爬取服务"""

    # 缓存配置：(前缀, 过期时间)
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
        self.config = AppConfig().get_web_scraper_config()
        self.base_url = self.config.get('javdb_url', "https://javdb.com")
        self._initialize_services()
        self.http_util = HttpUtil()
        self.parser = ParserFactory.get_parser()
        self._entity_cache = {}

    def _initialize_services(self):
        """初始化所有相关服务"""
        from app.services import (
            MovieService, ActorService, StudioService, DirectorService,
            GenreService, MagnetService, SeriesService, LabelService,
            ChartService, ChartTypeService, ChartEntryService,
            DownloadService, CacheService
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
            'cache': CacheService
        }

        for name, service_class in services.items():
            setattr(self, f'{name}_service', service_class())

    def process_charts(self):
        """处理所有榜单数据"""
        info("开始处理榜单数据")
        self._entity_cache.clear()

        try:
            chart_list = self.chart_service.parse_local_chartlist()
            chart_type = self._get_or_create_chart_type()

            for chart in chart_list:
                self._process_chart(chart, chart_type)
                db.session.commit()

            info("榜单处理完成")
        except Exception as e:
            db.session.rollback()
            error(f"处理榜单时出错: {str(e)}")
            raise

    def _get_or_create_chart_type(self) -> ChartType:
        """获取或创建榜单类型"""
        chart_type = self.chart_type_service.get_current_chart_type()
        db_type = self.chart_type_service.get_by_name(chart_type.name)
        if not db_type:
            db.session.add(chart_type)
            db.session.flush()
            db_type = chart_type
        return db_type

    def _process_chart(self, chart: Chart, chart_type: ChartType):
        """处理单个榜单及其条目"""
        info(f"处理榜单: {chart.name}")

        chart.chart_type = chart_type
        db_chart = self._get_or_create_chart(chart)

        for entry in chart.entries:
            self._process_chart_entry(entry, db_chart)
            db.session.flush()

    def _get_or_create_chart(self, chart: Chart) -> Chart:
        """获取或创建榜单"""
        db_chart = self.chart_service.get_by_name(chart.name)
        if not db_chart:
            db.session.add(chart)
            db.session.flush()
            db_chart = chart
        return db_chart

    def _process_chart_entry(self, entry: ChartEntry, chart: Chart):
        """处理榜单条目"""
        info(f"处理榜单条目: {entry.serial_number}")

        # 获取电影详情
        movie_data = self._get_movie_info(entry.serial_number)
        if not movie_data:
            return

        # 处理电影及其关联实体
        db_movie = self._process_movie(movie_data)
        if not db_movie:
            return

        # 处理榜单条目
        entry.chart = chart
        entry.movie = db_movie
        self._create_or_update_chart_entry(entry)

    def _get_movie_info(self, serial_number: str) -> Optional[Movie]:
        """获取电影详情页面信息"""
        search_url = f'{self.base_url}/search?q={serial_number}&f=all'
        soup = self.http_util.request(url=search_url, proxy_enable=self.config["proxy_enable"])
        if not soup:
            return None

        results = self.parser.parse_search_results(soup)
        if not results:
            return None

        detail_url = f'{self.base_url}{results[0].uri}'
        soup = self.http_util.request(url=detail_url, proxy_enable=self.config['proxy_enable'])
        return self.parser.parse_movie_details_page(soup) if soup else None

    def _process_movie(self, movie: Movie) -> Optional[Movie]:
        """处理电影及其关联实体"""
        # 先检查缓存和数据库
        db_movie = self._get_cached_or_db_movie(movie.serial_number)

        if db_movie:
            # 更新现有电影信息
            self._update_movie_relations(db_movie, movie)
            return db_movie
        else:
            # 创建新电影及其关联
            return self._create_new_movie(movie)

    def _get_cached_or_db_movie(self, serial_number: str) -> Optional[Movie]:
        """从缓存或数据库获取电影"""
        cache_key = f"movie:{serial_number}"

        # 检查内存缓存
        if cached := self._entity_cache.get(cache_key):
            return cached

        # 检查Redis缓存
        if redis_cached := self.cache_service.get(cache_key):
            movie = Movie.from_dict(redis_cached)
            self._entity_cache[cache_key] = movie
            return movie

        # 从数据库获取
        return self.movie_service.get_movie_from_db_by_serial_number(serial_number)

    def _update_movie_relations(self, db_movie: Movie, new_movie: Movie):
        """更新电影关联信息"""
        # 更新基本属性
        for attr in ['name', 'title', 'pic_cover', 'release_date', 'length',
                     'have_mg', 'have_file', 'have_hd', 'have_sub']:
            if hasattr(new_movie, attr):
                setattr(db_movie, attr, getattr(new_movie, attr))

        # 更新制作商
        if new_movie.studio:
            studio = self._get_or_create_entity(new_movie.studio, self.studio_service)
            db_movie.studio = studio

        # 更新其他关联实体
        relations = {
            'actors': self.actor_service,
            'directors': self.director_service,
            'genres': self.genre_service,
            'labels': self.label_service,
            'series': self.series_service
        }

        for attr, service in relations.items():
            if new_entities := getattr(new_movie, attr, None):
                existing = getattr(db_movie, attr)
                existing_names = {e.name for e in existing}

                for entity in new_entities:
                    if entity.name not in existing_names:
                        db_entity = self._get_or_create_entity(entity, service)
                        existing.append(db_entity)

        db.session.flush()

    def _create_new_movie(self, movie: Movie) -> Movie:
        """创建新电影及其关联"""
        # 处理制作商
        if movie.studio:
            movie.studio = self._get_or_create_entity(movie.studio, self.studio_service)

        # 处理其他关联实体
        relations = {
            'actors': self.actor_service,
            'directors': self.director_service,
            'genres': self.genre_service,
            'labels': self.label_service,
            'series': self.series_service
        }

        for attr, service in relations.items():
            if entities := getattr(movie, attr, None):
                setattr(movie, attr, [
                    self._get_or_create_entity(entity, service)
                    for entity in entities
                ])

        db.session.add(movie)
        db.session.flush()
        return movie

    def _get_or_create_entity(self, entity: Any, service: BaseService) -> Any:
        """获取或创建实体（带缓存）"""
        if not entity or not entity.name:
            return None

        entity_type = service.__class__.__name__.lower().replace('service', '')
        cache_key = f"{entity_type}:{entity.name}"

        # 检查内存缓存
        if cached := self._entity_cache.get(cache_key):
            return cached

        # 检查Redis缓存
        redis_key = f"{self.CACHE_CONFIG[entity_type][0]}{entity.name}"
        if redis_cached := self.cache_service.get(redis_key):
            entity_obj = type(entity).from_dict(redis_cached)
            self._entity_cache[cache_key] = entity_obj
            return entity_obj

        # 从数据库获取或创建
        db_entity = service.get_by_name(entity.name)
        if not db_entity:
            # 确保不设置ID，让数据库自动生成
            entity.id = None
            db.session.add(entity)
            db.session.flush()
            db_entity = entity

        # 更新缓存
        self._entity_cache[cache_key] = db_entity
        self.cache_service.set(
            redis_key,
            db_entity.to_dict(),
            self.CACHE_CONFIG[entity_type][1]
        )

        return db_entity

    def _create_or_update_chart_entry(self, entry: ChartEntry):
        """创建或更新榜单条目"""
        existing = self.chart_entry_service.get_by_chart_and_movie(
            entry.chart.id, entry.movie.id
        )

        if existing:
            existing.rank = entry.rank
            db.session.merge(existing)
        else:
            db.session.add(entry)

        db.session.flush()