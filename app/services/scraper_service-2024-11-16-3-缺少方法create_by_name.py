from typing import Optional, List
from sqlalchemy.orm import joinedload
from sqlalchemy.exc import IntegrityError
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
    """电影数据爬虫服务，负责从网页抓取电影信息并同步到数据库"""

    def __init__(self):
        self.config = AppConfig().get_web_scraper_config()
        self.base_url = self.config.get('javdb_url', "https://javdb.com")
        self._init_services()
        self.http_util = HttpUtil()
        self.parser = ParserFactory.get_parser()

    def _init_services(self):
        """初始化各类服务组件"""
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
            'chart_entry': ChartEntryService(),
        }

    def process_charts(self):
        """处理所有榜单数据"""
        info("开始处理榜单数据")
        try:
            charts = self.services['chart'].parse_local_chartlist()
            if not charts:
                info("未找到榜单数据")
                return

            chart_type = self.services['chart_type'].get_current_chart_type()
            if not chart_type:
                info("未找到有效的榜单类型")
                return

            for chart in charts:
                # 创建榜单副本以避免修改原始数据
                chart_entries = list(chart.entries)
                chart.chart_type = chart_type
                self._save_chart_and_entries(chart, chart_entries)

        except Exception as e:
            error(f"处理榜单数据时出错: {e}")

    def _save_chart_and_entries(self, chart: Chart, entries: List[ChartEntry]):
        """保存榜单及其条目"""
        info(f"处理榜单: {chart.name}")
        try:
            saved_chart = (self.services['chart'].get_by_name(chart.name) or
                           self.services['chart'].create(chart))

            for entry in entries:
                self._process_chart_entry(saved_chart, entry)
        except Exception as e:
            error(f"保存榜单 '{chart.name}' 时出错: {e}")

    def _process_chart_entry(self, chart: Chart, entry: ChartEntry):
        """处理单个榜单条目"""
        info(f"处理榜单条目: {entry.serial_number}")
        try:
            movie = self._get_or_create_movie(entry.serial_number)
            if not movie:
                return

            self._save_chart_entry(chart, movie, entry.rank)
        except Exception as e:
            error(f"处理榜单条目 '{entry.serial_number}' 时出错: {e}")

    def _save_chart_entry(self, chart: Chart, movie: Movie, rank: int):
        """保存或更新榜单条目"""
        try:
            existing_entry = self.services['chart_entry'].get_by_chart_and_movie(
                chart.id, movie.id)

            if existing_entry:
                existing_entry.rank = rank
                self.services['chart_entry'].update(existing_entry)
            else:
                new_entry = ChartEntry(chart=chart, movie=movie, rank=rank)
                self.services['chart_entry'].create(new_entry)
        except Exception as e:
            error(f"保存榜单条目时出错: {e}")

    def _get_or_create_movie(self, serial_number: str) -> Optional[Movie]:
        """获取或创建电影信息"""
        try:
            movie_info = self._fetch_movie_info(serial_number)
            if not movie_info:
                return None

            return self._save_movie_info(movie_info)
        except Exception as e:
            error(f"处理电影 '{serial_number}' 时出错: {e}")
            return None

    def _fetch_movie_info(self, serial_number: str) -> Optional[Movie]:
        """从网页获取电影详细信息"""
        info(f"搜索电影: {serial_number}")
        search_url = f'{self.base_url}/search?q={serial_number}&f=all'
        search_page = self.http_util.request(url=search_url)
        if not search_page:
            return None

        search_results = self.parser.parse_search_results(search_page)
        if not search_results:
            return None

        info(f"获取电影详情: {serial_number}")
        detail_url = f'{self.base_url}{search_results[0].uri}'
        detail_page = self.http_util.request(url=detail_url)
        if not detail_page:
            return None

        return self.parser.parse_movie_details_page(detail_page)

    def _save_movie_info(self, movie: Movie) -> Optional[Movie]:
        """保存电影信息到数据库"""
        try:
            existing_movie = self._get_movie_with_relations(movie.serial_number)
            return (self._update_movie(existing_movie, movie) if existing_movie
                    else self._create_new_movie(movie))
        except Exception as e:
            error(f"保存电影 '{movie.serial_number}' 时出错: {e}")
            return None

    def _get_movie_with_relations(self, serial_number: str) -> Optional[Movie]:
        """获取包含所有关联数据的电影信息"""
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

    def _update_movie(self, existing_movie: Movie, new_movie: Movie) -> Movie:
        """更新已存在的电影信息"""
        # 更新基本属性
        for field in ['name', 'title', 'pic_cover', 'release_date', 'length',
                      'have_mg', 'have_file', 'have_hd', 'have_sub']:
            if value := getattr(new_movie, field, None):
                setattr(existing_movie, field, value)

        # 更新关联实体
        self._update_relations(existing_movie, new_movie)
        return self.services['movie'].update(existing_movie)

    def _create_new_movie(self, movie: Movie) -> Optional[Movie]:
        """创建新的电影记录"""
        self._process_relations(movie)
        try:
            return self.services['movie'].create(movie)
        except IntegrityError:
            return self.services['movie'].get_movie_from_db_by_serial_number(
                movie.serial_number)

    def _update_relations(self, existing_movie: Movie, new_movie: Movie):
        """更新电影的关联实体"""
        # 更新制作公司
        if new_movie.studio:
            existing_movie.studio = self._get_or_create_entity(
                'studio', new_movie.studio.name)

        # 更新其他关联实体
        relation_types = {
            'actors': 'actor',
            'directors': 'director',
            'seriess': 'series',
            'genres': 'genre',
            'labels': 'label'
        }

        for relation_name, service_name in relation_types.items():
            existing_entities = getattr(existing_movie, relation_name)
            existing_names = {entity.name for entity in existing_entities}

            for new_entity in getattr(new_movie, relation_name, []):
                if new_entity.name not in existing_names:
                    db_entity = self._get_or_create_entity(
                        service_name, new_entity.name)
                    existing_entities.append(db_entity)

    def _process_relations(self, movie: Movie):
        """处理新电影的所有关联实体"""
        # 处理制作公司
        if movie.studio:
            movie.studio = self._get_or_create_entity(
                'studio', movie.studio.name)

        # 处理其他关联实体
        relation_types = {
            'actors': 'actor',
            'directors': 'director',
            'seriess': 'series',
            'genres': 'genre',
            'labels': 'label'
        }

        for relation_name, service_name in relation_types.items():
            entities = []
            for entity in getattr(movie, relation_name, []):
                db_entity = self._get_or_create_entity(service_name, entity.name)
                entities.append(db_entity)
            setattr(movie, relation_name, entities)

    def _get_or_create_entity(self, service_name: str, entity_name: str):
        """获取或创建关联实体"""
        service = self.services[service_name]
        return service.get_by_name(entity_name) or service.create_by_name(entity_name)