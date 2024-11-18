from typing import Optional, List, Dict
from sqlalchemy.orm import joinedload
from sqlalchemy.exc import IntegrityError
from functools import partial

from app.model.db.movie_model import Movie, Chart, ChartEntry, ChartType
from app.services import (
    MovieService, ActorService, StudioService, DirectorService,
    GenreService, SeriesService, LabelService, ChartService,
    ChartTypeService, ChartEntryService
)
from app.utils.http_util import HttpUtil
from app.utils.parser.parser_factory import ParserFactory
from app.config.log_config import info, error
from app.config.app_config import AppConfig


class ScraperService:
    """电影数据抓取与处理服务"""

    def __init__(self):
        config = AppConfig().get_web_scraper_config()
        self.base_url = config.get('javdb_url', "https://javdb.com")

        self.services = {
            'movie': MovieService(),
            'actor': ActorService(),
            'studio': StudioService(),
            'director': DirectorService(),
            'genre': GenreService(),
            'series': SeriesService(),
            'label': LabelService(),
            'chart': ChartService(),
            'chart_type': ChartTypeService(),
            'chart_entry': ChartEntryService()
        }

        self.http_util = HttpUtil()
        self.parser = ParserFactory.get_parser()

    def process_charts(self):
        """处理所有榜单数据"""
        try:
            chart_list = self.services['chart'].parse_local_chartlist()
            if not chart_list:
                info("未找到榜单数据")
                return

            for chart in list(chart_list):
                self._process_single_chart(chart)

        except Exception as e:
            error(f"榜单处理错误: {e}")

    def _process_single_chart(self, chart: Chart):
        """处理单个榜单数据"""
        info(f"处理榜单: {chart.name}")
        try:
            chart_entries = list(chart.entries)
            for entry in chart_entries:
                entry.chart_name = chart.name
                self._process_chart_entry(entry)

        except Exception as e:
            error(f"榜单 '{chart.name}' 处理错误: {e}")

    def _process_chart_entry(self, entry: ChartEntry):
        """处理榜单条目数据"""
        info(f"处理条目: {entry.serial_number}")
        movie = self._get_or_create_movie(entry.serial_number)

        if not movie:
            return

        self._save_chart_entry(entry, movie)

    def _save_chart_entry(self, entry: ChartEntry, movie: Movie):
        """保存榜单条目"""
        chart_type = self._get_chart_type()
        chart = Chart(name=entry.chart_name, chart_type=chart_type)

        db_chart = self.services['chart'].get_by_name(chart.name)
        entry.movie = movie

        if not db_chart:
            entry.chart = chart
            self.services['chart_entry'].create(entry)
        else:
            existing_entry = self.services['chart_entry'].get_by_chart_and_movie(
                db_chart.id, movie.id)

            if not existing_entry:
                entry.chart = db_chart
                self.services['chart_entry'].create(entry)

    def _get_chart_type(self) -> ChartType:
        """获取或创建榜单类型"""
        chart_type = self.services['chart_type'].get_current_chart_type()
        return self.services['chart_type'].get_by_name(chart_type.name) or chart_type

    def _get_or_create_movie(self, serial_number: str) -> Optional[Movie]:
        """获取或创建电影信息"""
        try:
            movie_info = self._fetch_movie_info(serial_number)
            return self._process_movie_data(movie_info) if movie_info else None
        except Exception as e:
            error(f"电影 '{serial_number}' 处理错误: {e}")
            return None

    def _fetch_movie_info(self, serial_number: str) -> Optional[Movie]:
        """获取电影详细信息"""
        info(f"搜索电影: {serial_number}")
        search_url = f'{self.base_url}/search?q={serial_number}&f=all'
        search_soup = self.http_util.request(url=search_url)

        if not search_soup:
            return None

        search_results = self.parser.parse_search_results(search_soup)

        if not search_results:
            return None

        info(f"获取电影详情: {serial_number}")
        detail_url = f'{self.base_url}{search_results[0].uri}'
        detail_soup = self.http_util.request(url=detail_url)

        return self.parser.parse_movie_details_page(detail_soup) if detail_soup else None

    def _process_movie_data(self, movie: Movie) -> Optional[Movie]:
        """处理电影数据"""
        if not movie:
            return None

        try:
            existing_movie = self._get_existing_movie(movie.serial_number)
            return (
                self._update_movie(existing_movie, movie)
                if existing_movie
                else self._create_movie(movie)
            )
        except Exception as e:
            error(f"电影 '{movie.serial_number}' 数据处理错误: {e}")
            return None

    def _get_existing_movie(self, serial_number: str) -> Optional[Movie]:
        """获取已存在的电影信息"""
        return self.services['movie'].get_movie_from_db_by_serial_number(
            serial_number,
            options=[
                joinedload(Movie.studio),
                joinedload(Movie.actors),
                joinedload(Movie.directors),
                joinedload(Movie.seriess),
                joinedload(Movie.genres),
                joinedload(Movie.labels)
            ]
        )

    def _create_movie(self, movie: Movie) -> Optional[Movie]:
        """创建新电影"""
        self._process_relations(movie)

        try:
            return self.services['movie'].create(movie)
        except IntegrityError:
            return self.services['movie'].get_movie_from_db_by_serial_number(
                movie.serial_number)

    def _update_movie(self, existing_movie: Movie, new_movie: Movie) -> Movie:
        """更新电影信息"""
        self._update_basic_info(existing_movie, new_movie)
        self._update_relations(existing_movie, new_movie)
        return self.services['movie'].update(existing_movie)

    def _update_basic_info(self, existing_movie: Movie, new_movie: Movie):
        """更新电影基本信息"""
        fields = ['name', 'title', 'pic_cover', 'release_date', 'length',
                  'have_mg', 'have_file', 'have_hd', 'have_sub']
        for field in fields:
            if value := getattr(new_movie, field, None):
                setattr(existing_movie, field, value)

    def _process_relations(self, movie: Movie):
        """处理电影关联数据"""
        relations = {
            'studio': 'studio_service',
            'actors': 'actor_service',
            'directors': 'director_service',
            'seriess': 'series_service',
            'genres': 'genre_service',
            'labels': 'label_service'
        }

        for attr, service_key in relations.items():
            service = self.services[service_key.replace('_service', '')]

            # 特殊处理studio（单个对象）
            if attr == 'studio':
                studio = getattr(movie, attr, None)
                if studio:
                    db_studio = service.get_by_name(studio.name) or service.create(studio)
                    setattr(movie, attr, db_studio)
            else:
                entities = []
                for entity in getattr(movie, attr, []):
                    db_entity = service.get_by_name(entity.name) or service.create(entity)
                    entities.append(db_entity)
                setattr(movie, attr, entities)

    def _handle_relation(self, movie: Movie, attr: str, service_key: str):
        """处理单个关系"""
        entities = []
        service = self.services[service_key.replace('_service', '')]

        for entity in getattr(movie, attr, []):
            db_entity = service.get_by_name(entity.name) or service.create(entity)
            entities.append(db_entity)

        setattr(movie, attr, entities)

    def _update_relations(self, existing_movie: Movie, new_movie: Movie):
        """更新电影关联数据"""
        relations = {
            'studio': 'studio_service',
            'actors': 'actor_service',
            'directors': 'director_service',
            'seriess': 'series_service',
            'genres': 'genre_service',
            'labels': 'label_service'
        }

        for attr, service_key in relations.items():
            service = self.services[service_key.replace('_service', '')]

            # 特殊处理studio（单个对象）
            if attr == 'studio':
                new_studio = getattr(new_movie, attr, None)
                if new_studio:
                    db_studio = service.get_by_name(new_studio.name) or service.create(new_studio)
                    setattr(existing_movie, attr, db_studio)
            else:
                existing_entities = getattr(existing_movie, attr)
                existing_names = {e.name for e in existing_entities}

                for entity in getattr(new_movie, attr, []):
                    if entity.name not in existing_names:
                        db_entity = service.get_by_name(entity.name) or service.create(entity)
                        existing_entities.append(db_entity)