from typing import Optional, List
from sqlalchemy.orm import joinedload, Session
from sqlalchemy.exc import IntegrityError
from app.model.db.movie_model import Movie, Chart, ChartEntry, ChartType
from app.services import (
    MovieService, ActorService, StudioService, DirectorService,
    GenreService, SeriesService, LabelService, ChartService,
    ChartTypeService, ChartEntryService
)
from app.utils.http_util import HttpUtil
from app.utils.parser.parser_factory import ParserFactory
from app.config.log_config import info
from app.config.app_config import AppConfig


class ScraperService:
    """电影数据抓取服务"""

    def __init__(self):
        self.config = AppConfig().get_web_scraper_config()
        self.base_url = self.config.get('javdb_url', "https://javdb.com")
        self._initialize_services()
        self.http_util = HttpUtil()
        self.parser = ParserFactory.get_parser()

    def _initialize_services(self):
        """初始化所需服务"""
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
        info("开始处理榜单")
        chart_list = self.services['chart'].parse_local_chartlist()
        if not chart_list:
            info("没有找到榜单数据")
            return

        chart_type = self.services['chart_type'].get_current_chart_type()
        if not chart_type:
            info("无法获取榜单类型")
            return

        for chart in chart_list:
            chart.chart_type = chart_type
            self._process_single_chart(chart)

    def _process_single_chart(self, chart: Chart):
        """处理单个榜单"""
        info(f"处理榜单: {chart.name}")
        db_chart = (self.services['chart'].get_by_name(chart.name) or
                    self.services['chart'].create(chart))

        for entry in chart.entries:
            entry.chart = db_chart
            self._process_chart_entry(entry)

    def _process_chart_entry(self, entry: ChartEntry):
        """处理榜单条目"""
        info(f"处理榜单条目: {entry.serial_number}")
        movie = self._get_or_create_movie(entry.serial_number)
        if not movie:
            return

        entry.movie = movie
        existing_entry = self.services['chart_entry'].get_by_chart_and_movie(
            entry.chart.id, movie.id)

        if existing_entry:
            existing_entry.rank = entry.rank
            self.services['chart_entry'].update(existing_entry)
        else:
            self.services['chart_entry'].create(entry)

    def _get_or_create_movie(self, serial_number: str) -> Optional[Movie]:
        """获取或创建电影信息"""
        movie_info = self._fetch_movie_details(serial_number)
        if not movie_info:
            return None

        processed_movie = self._process_movie_data(movie_info)
        return processed_movie

    def _fetch_movie_details(self, serial_number: str) -> Optional[Movie]:
        """从网页获取电影详情"""
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
        if not detail_soup:
            return None

        return self.parser.parse_movie_details_page(detail_soup)

    def _process_movie_data(self, movie: Movie) -> Optional[Movie]:
        """处理电影数据"""
        existing_movie = self.services['movie'].get_movie_from_db_by_serial_number(
            movie.serial_number,
            options=[
                joinedload(Movie.studio),
                joinedload(Movie.actors),
                joinedload(Movie.directors),
                joinedload(Movie.seriess),
                joinedload(Movie.genres),
                joinedload(Movie.labels)
            ]
        )

        if existing_movie:
            return self._update_movie(existing_movie, movie)
        else:
            return self._create_movie(movie)

    def _update_movie(self, existing_movie: Movie, new_movie: Movie) -> Movie:
        """更新电影信息"""
        for field in ['name', 'title', 'pic_cover', 'release_date', 'length',
                      'have_mg', 'have_file', 'have_hd', 'have_sub']:
            if value := getattr(new_movie, field, None):
                setattr(existing_movie, field, value)

        self._update_movie_relations(existing_movie, new_movie)
        return self.services['movie'].update(existing_movie)

    def _create_movie(self, movie: Movie) -> Optional[Movie]:
        """创建新电影"""
        self._process_movie_relations(movie)
        try:
            return self.services['movie'].create(movie)
        except IntegrityError:
            return self.services['movie'].get_movie_from_db_by_serial_number(
                movie.serial_number)

    def _update_movie_relations(self, existing_movie: Movie, new_movie: Movie):
        """更新电影关联关系"""
        if new_movie.studio:
            existing_movie.studio = (
                    self.services['studio'].get_by_name(new_movie.studio.name) or
                    self.services['studio'].create(new_movie.studio)
            )

        relations = {
            'actors': self.services['actor'],
            'directors': self.services['director'],
            'seriess': self.services['series'],
            'genres': self.services['genre'],
            'labels': self.services['label']
        }

        for rel_name, service in relations.items():
            existing = getattr(existing_movie, rel_name)
            existing_names = {e.name for e in existing}
            for entity in getattr(new_movie, rel_name, []):
                if entity.name not in existing_names:
                    db_entity = (
                            service.get_by_name(entity.name) or
                            service.create(entity)
                    )
                    existing.append(db_entity)

    def _process_movie_relations(self, movie: Movie):
        """处理新电影的关联关系"""
        if movie.studio:
            movie.studio = (
                    self.services['studio'].get_by_name(movie.studio.name) or
                    self.services['studio'].create(movie.studio)
            )

        relations = {
            'actors': self.services['actor'],
            'directors': self.services['director'],
            'seriess': self.services['series'],
            'genres': self.services['genre'],
            'labels': self.services['label']
        }

        for rel_name, service in relations.items():
            processed_entities = []
            for entity in getattr(movie, rel_name, []):
                db_entity = (
                        service.get_by_name(entity.name) or
                        service.create(entity)
                )
                processed_entities.append(db_entity)
            setattr(movie, rel_name, processed_entities)