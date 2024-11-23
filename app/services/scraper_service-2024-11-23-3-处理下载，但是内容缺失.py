from typing import Optional, List, Tuple, Dict, Any, Union
from sqlalchemy.orm import joinedload
from sqlalchemy.exc import IntegrityError

from app.model.db.movie_model import Movie, Chart, ChartEntry, ChartType
from app.services import (
    MovieService, ActorService, StudioService, DirectorService,
    GenreService, SeriesService, LabelService, ChartService,
    ChartTypeService, ChartEntryService, MagnetService, DownloadService, EverythingService, JellyfinService
)
from app.utils.download_client import DownloadStatus
from app.utils.http_util import HttpUtil
from app.utils.parser.parser_factory import ParserFactory
from app.config.log_config import info, error
from app.config.app_config import AppConfig

class ScraperService:
    """电影数据抓取与处理服务"""

    # 实体关系映射配置
    ENTITY_MAPPINGS = {
        'studio': ('studio', False),      # False表示一对多关系
        'actors': ('actor', True),        # True表示多对多关系
        'directors': ('director', True),
        'seriess': ('series', True),
        'genres': ('genre', True),
        'labels': ('label', True)
    }

    # Movie表的预加载关系配置
    MOVIE_PRELOAD_RELATIONS = [
        joinedload(Movie.studio),
        joinedload(Movie.actors),
        joinedload(Movie.directors),
        joinedload(Movie.seriess),
        joinedload(Movie.genres),
        joinedload(Movie.labels)
    ]

    def __init__(self):
        config = AppConfig().get_web_scraper_config()
        self.base_url = config.get('javdb_url', "https://javdb.com")
        self._init_services()
        self.http_util = HttpUtil()
        self.parser = ParserFactory.get_parser()

    def _init_services(self) -> None:
        """初始化服务"""
        self.service_map = {
            'movie': MovieService(),
            'actor': ActorService(),
            'studio': StudioService(),
            'director': DirectorService(),
            'genre': GenreService(),
            'series': SeriesService(),
            'label': LabelService(),
            'chart': ChartService(),
            'chart_type': ChartTypeService(),
            'chart_entry': ChartEntryService(),
            'magnet': MagnetService(),
            'download': DownloadService(),
            'everything': EverythingService(),
            'jellyfin': JellyfinService()
        }

    def process_all_charts(self) -> None:
        """处理所有榜单数据"""
        try:
            charts = self.service_map['chart'].parse_local_chartlist()
            if not charts:
                info("未找到榜单数据")
                return

            for chart in charts:
                self._process_chart(chart)
        except Exception as e:
            error(f"榜单处理出错: {str(e)}")

    def _process_chart(self, chart: Chart) -> None:
        """处理单个榜单数据"""
        info(f"正在处理榜单: {chart.name}")
        try:
            chart_entries = list(chart.entries)
            for entry in chart_entries:
                if movie := self._fetch_and_process_movie(entry.serial_number):
                    self._save_chart_entry(entry, movie, chart.name)
        except Exception as e:
            error(f"处理榜单 '{chart.name}' 时出错: {str(e)}")

    def _fetch_movie_info(self, serial_number: str) -> Optional[Movie]:
        """从网页抓取电影详细信息"""
        search_url = f'{self.base_url}/search?q={serial_number}&f=all'
        if not (search_page := self.http_util.request(url=search_url)):
            return None

        if not (search_results := self.parser.parse_search_results(search_page)):
            return None

        detail_url = f'{self.base_url}{search_results[0].uri}'
        if not (detail_page := self.http_util.request(url=detail_url)):
            return None

        return self.parser.parse_movie_details_page(detail_page)

    def _fetch_and_process_movie(self, serial_number: str) -> Optional[Movie]:
        """获取并处理电影信息"""
        info(f"正在处理电影: {serial_number}")
        try:
            if not (movie_info := self._fetch_movie_info(serial_number)):
                return None

            # 处理下载状态
            movie_info.download_status = self._process_movie_download(movie=movie_info)

            existing_movie = self._get_existing_movie(serial_number)
            return (
                self._update_movie(existing_movie, movie_info)
                if existing_movie
                else self._create_new_movie(movie_info)
            )
        except Exception as e:
            error(f"处理电影 '{serial_number}' 时出错: {str(e)}")
            return None

    def _get_existing_movie(self, serial_number: str) -> Optional[Movie]:
        """从数据库获取已存在的电影信息"""
        return self.service_map['movie'].get_movie_from_db_by_serial_number(
            serial_number,
            options=self.MOVIE_PRELOAD_RELATIONS
        )

    def _process_entity(self, entity: Any, service_key: str) -> Optional[Any]:
        """处理单个实体，确保清理关系并返回数据库实体"""
        if not entity:
            return None

        # 清理实体关系，避免级联创建
        for rel in ['movies', 'actors', 'directors', 'genres', 'labels', 'seriess']:
            if hasattr(entity, rel):
                setattr(entity, rel, [])

        return (
            self.service_map[service_key].get_by_name(entity.name) or
            self.service_map[service_key].create(entity)
        )

    def _process_relations(self, movie: Movie, is_update: bool = False) -> None:
        """统一处理电影的所有关联实体"""
        for attr, (service_key, is_many) in self.ENTITY_MAPPINGS.items():
            if not hasattr(movie, attr):
                continue

            entities = getattr(movie, attr)
            if not entities:
                continue

            if is_many:
                # 处理多对多关系
                existing_entities = getattr(movie, attr) if is_update else []
                existing_names = {e.name for e in existing_entities}

                new_entities = []
                for entity in (entities if isinstance(entities, list) else [entities]):
                    if is_update and entity.name in existing_names:
                        continue
                    if processed := self._process_entity(entity, service_key):
                        new_entities.append(processed)

                if is_update:
                    existing_entities.extend(new_entities)
                    setattr(movie, attr, existing_entities)
                else:
                    setattr(movie, attr, new_entities)
            else:
                # 处理一对多关系
                processed = self._process_entity(entities, service_key)
                setattr(movie, attr, processed)

    def _create_new_movie(self, movie: Movie) -> Optional[Movie]:
        """创建新电影记录"""
        self._process_relations(movie)
        try:
            return self.service_map['movie'].create(movie)
        except IntegrityError:
            return self.service_map['movie'].get_movie_from_db_by_serial_number(
                movie.serial_number)

    def _update_movie(self, existing: Movie, new: Movie) -> Movie:
        """更新已存在的电影信息"""
        # 更新基础字段
        basic_fields = [
            'name', 'title', 'pic_cover', 'release_date', 'length',
            'have_mg', 'have_file', 'have_hd', 'have_sub'
        ]
        for field in basic_fields:
            if value := getattr(new, field, None):
                setattr(existing, field, value)

        # 更新关联实体
        self._process_relations(new, is_update=True)
        return self.service_map['movie'].update(existing)

    def _save_chart_entry(self, entry: ChartEntry, movie: Movie, chart_name: str) -> None:
        """保存榜单条目"""
        # 获取或创建榜单类型
        chart_type = (
            self.service_map['chart_type'].get_current_chart_type() or
            self.service_map['chart_type'].create(ChartType())
        )

        # 获取或创建榜单
        chart = Chart(name=chart_name, chart_type=chart_type)
        db_chart = (
            self.service_map['chart'].get_by_name(chart_name) or
            self.service_map['chart'].create(chart)
        )

        # 创建条目（如果不存在）
        if not (existing_entry := self.service_map['chart_entry'].get_by_chart_and_movie(db_chart.id, movie.id)):
            entry.movie = movie
            entry.chart = db_chart
            self.service_map['chart_entry'].create(entry)
        else:
            if not existing_entry.movie or existing_entry.movie.id != movie.id:
                existing_entry.movie = movie
                self.chart_entry_service.update(existing_entry)

    def _process_movie_download(self, movie: Movie) -> int:
        """处理电影下载状态"""
        try:
            if self.service_map['jellyfin'].check_movie_exists(title=movie.serial_number):
                return DownloadStatus.IN_LIBRARY.value
            elif self.service_map['everything'].local_exists_movie(movie.serial_number):
                return DownloadStatus.COMPLETED.value

            if not movie.have_mg or not movie.magnets:
                return DownloadStatus.NO_SOURCE.value

            status = self.service_map['download'].get_download_status(movie.serial_number)

            # 已完成状态直接返回
            if status in [DownloadStatus.COMPLETED.value, DownloadStatus.IN_LIBRARY.value]:
                return status

            # 添加下载任务
            magnet = movie.magnets[0]
            if self.service_map['download'].add_download(f"magnet:?xt=urn:btih:{magnet.magnet_xt}"):
                return DownloadStatus.DOWNLOADING.value

            return DownloadStatus.DOWNLOAD_FAILED.value
        except Exception as e:
            error(f"处理电影下载状态时发生错误：{e}")
            return DownloadStatus.ERROR.value