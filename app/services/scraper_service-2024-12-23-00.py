import asyncio
from typing import List, Optional, Dict, Any
from bs4 import BeautifulSoup
from datetime import datetime
import json
from functools import lru_cache
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager

from app.config.app_config import AppConfig
from app.model.db.movie_model import Movie, Chart, ChartEntry, ChartType, Studio

from app.services.base_service import BaseService
from app.utils.download_client import DownloadStatus
from app.utils.http_util import HttpUtil
from app.utils.page_parser_util import PageParserUtil
from app.config.log_config import debug, info, warning, error, critical
from app.utils.parser.parser_factory import ParserFactory


class ScraperService:
    """
    电影数据爬取服务

    负责从网页抓取电影信息、处理榜单数据、管理下载任务等核心功能。
    实现了缓存机制和并发处理以提升性能。
    """

    # 缓存配置
    CACHE_CONFIG = {
        'movie': ('movie_from_db:', 24 * 3600),  # 24小时
        'actor': ('actor_from_db:', 24 * 3600),
        'director': ('director_from_db:', 24 * 3600),
        'series': ('series_from_db:', 24 * 3600),
        'studio': ('studio_from_db:', 24 * 3600),
        'genre': ('genre_from_db:', 24 * 3600),
        'label': ('label_from_db:', 24 * 3600)
    }

    def __init__(self):
        self._initialize_config()
        self._initialize_services()
        self._initialize_utils()
        self.failed_entries = []
        self.thread_pool = ThreadPoolExecutor(max_workers=4)

    def _initialize_config(self):
        """初始化配置"""
        self.config = AppConfig().get_web_scraper_config()
        self.base_url = self.config.get('javdb_url', "https://javdb.com")

    def _initialize_services(self):
        """初始化所有服务实例"""
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

    def _initialize_utils(self):
        """初始化工具类"""
        self.http_util = HttpUtil()
        self.page_parser = PageParserUtil()
        self.parser = ParserFactory.get_parser()

    @contextmanager
    def _error_handling(self, chart_entry: ChartEntry, operation: str):
        """统一的错误处理上下文管理器"""
        try:
            yield
        except Exception as e:
            error_msg = f"{operation} failed: {str(e)}"
            debug(f"Error processing entry {chart_entry.serial_number}: {error_msg}")
            self._add_failed_entry(chart_entry, error_msg)
            raise

    def process_charts(self):
        """处理所有榜单数据"""
        info("Starting chart processing")
        chart_list = self.chart_service.parse_local_chartlist()

        try:
            for chart in chart_list:
                self._process_chart(chart)
        finally:
            self._save_failed_entries()

        info("Chart processing completed")

    def _process_chart(self, chart: Chart):
        """处理单个榜单及其条目"""
        info(f"Processing chart: {chart.name}")
        chart = self._process_chart_type(chart)

        # 并发处理榜单条目
        futures = []
        for entry in chart.entries:
            entry.chart = chart
            future = self.thread_pool.submit(self._process_chart_entry, entry)
            futures.append(future)

        # 等待所有任务完成
        for future in futures:
            try:
                future.result()
            except Exception as e:
                debug(f"Chart entry processing failed: {str(e)}")

    def _process_chart_type(self, chart: Chart) -> Chart:
        """处理榜单类型"""
        chart_from_db = self.chart_service.get_by_name(chart.name)
        if chart_from_db:
            chart.id = chart_from_db.id

        default_type = self.chart_type_service.get_current_chart_type()
        type_from_db = self.chart_type_service.get_by_name(default_type.name)
        chart.chart_type = type_from_db or default_type

        return chart

    async def _process_chart_entry(self, chart_entry: ChartEntry) -> None:
        """
        处理单个榜单条目

        Args:
            chart_entry: 榜单条目实体

        主要流程：
        1. 爬取并解析电影信息
        2. 处理关联实体(演员、导演等)
        3. 更新或创建电影记录
        4. 处理下载状态
        5. 更新榜单排名信息
        """
        try:
            # 获取电影信息
            parsed_movie = await self._parse_movie(chart_entry)
            if not parsed_movie:
                self._add_failed_entry(
                    chart_entry,
                    'Failed to get movie information'
                )
                return

            # 处理关联实体
            self._process_related_entities(parsed_movie)

            # 获取或创建电影记录
            #movie = self._update_or_create_movie(parsed_movie, chart_entry)


            # 更新下载状态
            parsed_movie.download_status = self._process_movie_download(parsed_movie)

            # 保存电影信息
            chart_entry.movie = movie

            # 处理榜单排名
            await self._update_chart_entry(chart_entry)

            info(
                f"Successfully processed chart entry: {chart_entry.serial_number}"
            )

        except Exception as e:
            error_msg = f"Error processing chart entry {chart_entry.serial_number}: {str(e)}"
            error(error_msg)
            self._add_failed_entry(chart_entry, error_msg)
            raise

    def _get_movie_page_url(self, chart_entry: ChartEntry) -> str:
        """获取电影页面URL"""
        if chart_entry.link:
            return chart_entry.link

        # 搜索获取URL
        uri = self._search_movie_get_uri(chart_entry.serial_number)
        if uri:
            return f'{self.base_url}{uri}'
        return None

    def _search_movie_get_uri(self, serial_number: str) -> Optional[str]:
        """搜索电影获取URI"""
        search_url = f'{self.base_url}/search?q={serial_number}&f=all'
        soup = self.http_util.request(
            url=search_url,
            proxy_enable=self.config["proxy_enable"]
        )
        if soup:
            return self.extract_movie_page_uri(soup)
        return None

    def extract_movie_page_uri(self, soup: BeautifulSoup) -> Optional[str]:
        """从搜索结果提取电影页面URI"""
        results = self.parser.parse_search_results(soup)
        return results[0].uri if results else None

    def _process_movie_download(self, movie: Movie) -> int:
        """处理电影下载状态"""
        if not movie.have_mg or not movie.magnets:
            return DownloadStatus.NO_SOURCE.value

        status = self.download_service.get_download_status(movie.serial_number)

        # 已完成状态直接返回
        if status in [DownloadStatus.COMPLETED.value, DownloadStatus.IN_LIBRARY.value]:
            return status

        # 处理下载中或新下载的情况
        if not status or status <= DownloadStatus.DOWNLOADING.value:
            magnet = movie.magnets[0]

            # 检查下载速度并切换磁力链接
            if status == DownloadStatus.DOWNLOADING.value:
                if not self.download_service.check_download_speed(movie.serial_number):
                    magnet = self.download_service.get_next_magnet(
                        movie.serial_number,
                        movie.magnets
                    )

            # 添加下载任务
            if self.download_service.add_download(
                    f"magnet:?xt=urn:btih:{magnet.magnet_xt}"
            ):
                return DownloadStatus.DOWNLOADING.value

        return DownloadStatus.DOWNLOAD_FAILED.value

    def _process_related_entities(self, movie: Movie):
        """处理电影相关实体,"""
        # 定义实体处理映射
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
                    processed_entity = self._process_related_entity(
                        entity,
                        service,
                        cache_type
                    )
                    if processed_entity:
                        processed.append(processed_entity)

                # 更新关系
                getattr(movie, attr).clear()
                for entity in processed:
                    getattr(movie, attr).append(entity)
            else:
                setattr(movie, attr, self._process_related_entity(
                    entities,
                    service,
                    cache_type
                ))

    def _process_related_entity(self, entity: Any, service: BaseService, cache_type: str) -> Any:
        """处理单个关联实体"""
        if not entity or not entity.name:
            return None

        # 检查缓存
        cached_entity = self._get_cached_entity(cache_type, entity.name)

        if cached_entity:
            entity = entity.from_dict(cached_entity)

        # 先从数据库查询
        db_entity = service.get_by_name(entity.name)
        if db_entity:
            self._cache_entity(cache_type, entity.to_dict())
            entity.id = db_entity.id
        return entity

    def _get_cached_entity(self, cache_type: str, name: str) -> Optional[Dict[str, Any]]:
        """从缓存获取实体"""
        cache_key = f"{self.CACHE_CONFIG[cache_type][0]}{name}"
        return self.cache_service.get(cache_key)

    def _cache_entity(self, cache_type: str, entity: Any):
        """缓存实体"""
        if not entity or not entity.name:
            return

        cache_key = f"{self.CACHE_CONFIG[cache_type][0]}{entity.name}"
        self.cache_service.set(cache_key, entity.to_dict(), self.CACHE_CONFIG[cache_type][1])

    def _get_or_create_movie(self, parsed_movie: Movie, chart_entry: ChartEntry) -> Optional[Movie]:
        """获取或创建电影记录"""
        movie = self.movie_service.get_movie_from_db_by_serial_number(
            chart_entry.serial_number
        )

        if movie:
            return self._update_movie_info(movie, parsed_movie)

        parsed_movie.download_status = DownloadStatus.CRAWLED.value
        return parsed_movie

    def _update_movie_info(self, current: Movie, parsed: Movie) -> Movie:
        """更新电影信息"""
        update_attrs = [
            'title', 'name', 'name_cn', 'name_en', 'pic_cover',
            'release_date', 'length', 'score', 'actors', 'directors',
            'series', 'studio', 'genres', 'labels', 'magnets'
        ]

        for attr in update_attrs:
            new_value = getattr(parsed, attr, None)
            if new_value:
                setattr(current, attr, new_value)

        return current

    def _save_failed_entries(self):
        """保存处理失败的条目"""
        if not self.failed_entries:
            return

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"failed_entries_{timestamp}.json"

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.failed_entries, f, ensure_ascii=False, indent=2)

        info(f"Failed entries saved to {filename}")

    def cleanup(self):
        """清理资源"""
        self.thread_pool.shutdown(wait=True)

    # ---------- 优化？
    async def _parse_movie(self, chart_entry: ChartEntry) -> Optional[Movie]:
        """
        获取或解析电影信息

        Args:
            chart_entry: 榜单条目

        Returns:
            解析后的电影实体或None
        """
        # 获取页面URL
        url = self._get_movie_page_url(chart_entry)
        if not url:
            error(f"Failed to get movie URL for {chart_entry.serial_number}")
            raise ValueError("获取页面URL失败")
        # 解析电影信息
        soup = self.http_util.request(url=url, proxy_enable=self.config.proxy_enable)
        if not soup:
            return None
        parsed_movie = self.parser.parse_movie_details_page(soup)

        # 检查缓存
        cache_key = f"movie:{chart_entry.serial_number}"

        movie_from_db = None
        cached_movie = self.cache_service.get(cache_key)

        if cached_movie:
            movie_from_db = Movie.from_dict(cached_movie)

        else:

            movie_from_db = self.movie_service.get_movie_from_db_by_serial_number(chart_entry.serial_number)
            self.cache_service.set(cache_key, movie_from_db.to_dict(), self.config.cache_expire_time)

        if movie_from_db:
            parsed_movie.id = movie_from_db.id
            # 更新电影信息 暂时不更新
            # self._process_movie_info(movie_from_db, parsed_movie)

        parsed_movie.download_status = DownloadStatus.CRAWLED.value
        return parsed_movie

    def _process_movie_info(self, current: Movie, parsed: Movie) -> Movie:
        """合并电影信息"""
        update_attrs = [
            'title', 'name', 'name_cn', 'name_en', 'pic_cover', 'release_date',
            'length', 'score', 'actors', 'directors', 'series', 'studio',
            'genres', 'labels', 'magnets'
        ]

        for attr in update_attrs:
            if hasattr(parsed, attr):
                new_value = getattr(parsed, attr)
                if new_value:  # 只更新非空值
                    setattr(current, attr, new_value)

        return current

    async def _update_or_create_movie(
            self,
            parsed_movie: Movie,
            chart_entry: ChartEntry
    ) -> Optional[Movie]:
        """
        更新或创建电影记录

        Args:
            parsed_movie: 解析得到的电影信息
            chart_entry: 榜单条目

        Returns:
            更新或创建后的电影实体
        """
        try:
            # 查询现有记录
            existing_movie = self.movie_service.get_by_serial_number(
                chart_entry.serial_number
            )

            if existing_movie:
                # 更新现有记录
                movie = await self._merge_movie_info(existing_movie, parsed_movie)
            else:
                # 创建新记录
                parsed_movie.download_status = DownloadStatus.CRAWLED.value
                movie = parsed_movie

            return movie

        except Exception as e:
            error(
                f"Error updating/creating movie {chart_entry.serial_number}: {str(e)}"
            )
            return None

    def _merge_movie_info(
            self,
            current: Movie,
            parsed: Movie
    ) -> Movie:
        """
        合并电影信息

        Args:
            current: 数据库中现有的电影信息
            parsed: 新解析的电影信息

        Returns:
            合并后的电影实体
        """
        try:
            update_attrs = [
                'title', 'name', 'name_cn', 'name_en', 'pic_cover',
                'release_date', 'length', 'score',
                'actors', 'directors', 'series', 'studio',
                'genres', 'labels', 'magnets'
            ]

            for attr in update_attrs:
                if hasattr(parsed, attr):
                    new_value = getattr(parsed, attr)
                    if new_value:  # 只更新非空值
                        if isinstance(new_value, (list, set)):
                            # 处理关系集合
                            current_set = set(getattr(current, attr))
                            new_set = set(new_value)
                            setattr(current, attr, list(current_set | new_set))
                        else:
                            # 处理普通属性
                            setattr(current, attr, new_value)

            return current

        except Exception as e:
            error(f"Error merging movie info: {str(e)}")
            raise

    async def _update_chart_entry(self, chart_entry: ChartEntry) -> None:
        """
        更新榜单条目排名信息

        Args:
            chart_entry: 榜单条目
        """

        if not (chart_entry.chart.id and chart_entry.movie.id):
            self.chart_entry_service.create(chart_entry)
            return
        self.chart_entry_service.create(chart_entry)
        return

    def _add_failed_entry(self, chart_entry: ChartEntry, error: str) -> None:
        """
        添加失败记录

        Args:
            chart_entry: 处理失败的榜单条目
            error: 错误信息
        """
        failed_entry = {
            'serial_number': chart_entry.serial_number,
            'chart_name': chart_entry.chart.name,
            'error': error,
            'timestamp': datetime.now().isoformat()
        }
        self.failed_entries.append(failed_entry)
        error(f"Added failed entry: {json.dumps(failed_entry)}")
