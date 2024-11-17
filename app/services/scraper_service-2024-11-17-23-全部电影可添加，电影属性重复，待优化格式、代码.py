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
    """电影数据抓取服务"""

    def __init__(self):
        self.config = AppConfig().get_web_scraper_config()
        self.base_url = self.config.get('javdb_url', "https://javdb.com")
        self._initialize_services()
        self.http_util = HttpUtil()
        self.parser = ParserFactory.get_parser()

    def _initialize_services(self):
        """初始化相关服务"""
        """初始化相关服务"""
        self.movie_service = MovieService()
        self.actor_service = ActorService()
        self.studio_service = StudioService()
        self.director_service = DirectorService()
        self.genre_service = GenreService()
        self.series_service = SeriesService()
        self.label_service = LabelService()
        self.chart_service = ChartService()
        self.chart_type_service = ChartTypeService()
        self.chart_entry_service = ChartEntryService()

    def process_charts(self):
        """处理所有榜单数据"""
        info("开始处理榜单")
        try:
            chart_list = self.chart_service.parse_local_chartlist()
            if not chart_list:
                info("没有找到榜单数据")
                return

            # 1.将榜单数据转换为列表以避免迭代器消耗问题
            # charts = list(chart_list)
            # 2.使用列表复制避免迭代时修改问题
            for chart in chart_list[:]:
                # chart.chart_type = chart_type
                self._process_single_chart(chart)

        except Exception as e:
            error(f"处理榜单时出现错误: {e}")

    def _process_single_chart(self, chart: Chart):
        """处理单个榜单数据"""
        info(f"处理榜单: {chart.name}")
        try:
            # db_chart = (self.chart_service.get_by_name(chart.name) or
            # self.chart_service.create(chart))

            # 创建entries的副本进行迭代
            entries = list(chart.entries)
            for entry in entries:
                entry.chart_name = chart.name
                self._process_chart_entry(entry)

        except Exception as e:
            error(f"处理榜单 '{chart.name}' 时出现错误: {e}")

    def _process_chart_entry(self, entry: ChartEntry):
        """处理榜单条目数据"""
        info(f"处理榜单条目: {entry.serial_number}")
        movie = self._get_or_create_movie(entry.serial_number)
        if not movie:
            return

        try:
            self._save_chart_entry(entry, movie)
        except Exception as e:
            error(f"保存榜单条目时出现错误: {e}")

    def _save_chart_entry(self, entry: ChartEntry, movie: Movie):
        """保存榜单条目"""

        chart_type = self.chart_type_service.get_current_chart_type()
        if not chart_type:
            info("无法获取榜单类型")
            return
        db_chart_type = self.chart_type_service.get_by_name(chart_type.name)
        if db_chart_type:
            chart_type = db_chart_type

        chart = Chart(name=entry.chart_name, chart_type=chart_type)

        db_chart = self.chart_service.get_by_name(chart.name)

        entry.movie = movie
        if db_chart:
            # 数据库中存在榜单，添加到榜单关联。
            existing_entry = self.chart_entry_service.get_by_chart_and_movie(
                entry.chart.id, movie.id)
            if existing_entry:
                if not existing_entry.movie or existing_entry.movie.id != movie.id:
                    existing_entry.movie
                    self.chart_entry_service.update(existing_entry)

            else:
                entry.chart = db_chart
                self.chart_entry_service.create(entry)
        else:
            # 不存在，创建即可
            # 榜单不存在，就不可能存在条目
            entry.chart = chart
            self.chart_entry_service.create(entry)

    def _get_or_create_movie(self, serial_number: str) -> Optional[Movie]:
        """获取或创建电影信息"""
        try:
            movie_info = self._fetch_movie_info(serial_number)
            return self._process_movie_data(movie_info) if movie_info else None
        except Exception as e:
            error(f"处理电影 '{serial_number}' 时出现错误: {e}")
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
            return (self._update_movie(existing_movie, movie)
                    if existing_movie else self._create_movie(movie))
        except Exception as e:
            error(f"处理电影 '{movie.serial_number}' 数据时出现错误: {e}")
            return None

    def _get_existing_movie(self, serial_number: str) -> Optional[Movie]:
        """获取已存在的电影信息"""
        return self.movie_service.get_movie_from_db_by_serial_number(
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
            return self.movie_service.create(movie)
        except IntegrityError:
            return self.movie_service.get_movie_from_db_by_serial_number(
                movie.serial_number)

    def _update_movie(self, existing_movie: Movie, new_movie: Movie) -> Movie:
        """更新电影信息"""
        self._update_basic_info(existing_movie, new_movie)
        self._update_relations(existing_movie, new_movie)
        return self.movie_service.update(existing_movie)

    def _update_basic_info(self, existing_movie: Movie, new_movie: Movie):
        """更新电影基本信息"""
        fields = ['name', 'title', 'pic_cover', 'release_date', 'length',
                  'have_mg', 'have_file', 'have_hd', 'have_sub']
        for field in fields:
            if value := getattr(new_movie, field, None):
                setattr(existing_movie, field, value)

    def _process_relations(self, movie: Movie):
        """处理电影关联数据"""
        if movie.studio:
            movie.studio = self._get_or_create_entity(self.studio_service, movie.studio)

        relations = {
            'actors': self.actor_service,
            'directors': self.director_service,
            'seriess': self.series_service,
            'genres': self.genre_service,
            'labels': self.label_service
        }

        for attr_name, service in relations.items():
            entities = []
            for entity in getattr(movie, attr_name, []):
                db_entity = self._get_or_create_entity(service, entity)
                if db_entity:
                    entities.append(db_entity)
            setattr(movie, attr_name, entities)

    def _update_relations(self, existing_movie: Movie, new_movie: Movie):
        """更新电影关联数据"""
        if new_movie.studio:
            existing_movie.studio = self._get_or_create_entity(self.studio_service, new_movie.studio)

        relations = {
            'actors': self.actor_service,
            'directors': self.director_service,
            'seriess': self.series_service,
            'genres': self.genre_service,
            'labels': self.label_service
        }

        for attr_name, service in relations.items():
            existing = getattr(existing_movie, attr_name)
            existing_names = {e.name for e in existing}
            for entity in getattr(new_movie, attr_name, []):
                if entity.name not in existing_names:
                    db_entity = self._get_or_create_entity(service, entity)
                    if db_entity:
                        existing.append(db_entity)

    def _get_or_create_entity(self, service, entity):
        """获取或创建实体"""
        # service = self.services[service_name] if isinstance(service_name, str) else service_name
        return service.get_by_name(entity.name) or service.create(entity)
