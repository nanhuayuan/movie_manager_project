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
        self._init_services()
        self.http_util = HttpUtil()
        self.parser = ParserFactory.get_parser()

    def _init_services(self):
        """初始化服务组件"""
        service_classes = {
            'movie': MovieService,
            'actor': ActorService,
            'studio': StudioService,
            'director': DirectorService,
            'genre': GenreService,
            'series': SeriesService,
            'label': LabelService,
            'chart': ChartService,
            'chart_type': ChartTypeService,
            'chart_entry': ChartEntryService
        }
        self.services = {name: cls() for name, cls in service_classes.items()}

    def process_charts(self):
        """处理榜单数据流程"""
        info("开始处理榜单")
        chart_type = self._get_chart_type()
        if not chart_type:
            return

        charts = self._get_charts()
        if not charts:
            return

        # 创建charts的副本以避免迭代时修改问题
        for chart in list(charts):
            chart.chart_type = chart_type
            self._process_single_chart(chart)

    def _get_chart_type(self) -> Optional[ChartType]:
        """获取当前榜单类型"""
        try:
            return self.services['chart_type'].get_current_chart_type()
        except Exception as e:
            error(f"获取榜单类型失败: {e}")
            return None

    def _get_charts(self) -> Optional[List[Chart]]:
        """获取榜单列表"""
        try:
            charts = self.services['chart'].parse_local_chartlist()
            if not charts:
                info("未找到榜单数据")
                return None
            return charts
        except Exception as e:
            error(f"解析榜单数据失败: {e}")
            return None

    def _process_single_chart(self, chart: Chart):
        """处理单个榜单及其条目"""
        info(f"处理榜单: {chart.name}")
        try:
            db_chart = self._get_or_create_chart(chart)
            # 创建entries的副本以避免迭代时修改问题
            for entry in list(chart.entries):
                entry.chart = db_chart
                self._process_chart_entry(entry)
        except Exception as e:
            error(f"处理榜单 '{chart.name}' 失败: {e}")

    def _get_or_create_chart(self, chart: Chart) -> Chart:
        """获取或创建榜单"""
        return (self.services['chart'].get_by_name(chart.name) or
                self.services['chart'].create(chart))

    def _process_chart_entry(self, entry: ChartEntry):
        """处理榜单条目"""
        info(f"处理榜单条目: {entry.serial_number}")
        movie = self._get_or_create_movie(entry.serial_number)
        if not movie:
            return

        try:
            self._update_or_create_chart_entry(entry, movie)
        except Exception as e:
            error(f"保存榜单条目失败: {e}")

    def _update_or_create_chart_entry(self, entry: ChartEntry, movie: Movie):
        """更新或创建榜单条目"""
        entry.movie = movie
        existing_entry = self.services['chart_entry'].get_by_chart_and_movie(
            entry.chart.id, movie.id)
        if existing_entry:
            existing_entry.rank = entry.rank
            self.services['chart_entry'].update(existing_entry)
        else:
            self.services['chart_entry'].create(entry)

    def _get_or_create_movie(self, serial_number: str) -> Optional[Movie]:
        """获取或创建电影记录"""
        movie_info = self._fetch_movie_info(serial_number)
        if not movie_info:
            return None

        try:
            return self._process_movie_data(movie_info)
        except Exception as e:
            error(f"处理电影 '{serial_number}' 数据失败: {e}")
            return None

    def _fetch_movie_info(self, serial_number: str) -> Optional[Movie]:
        """获取电影详细信息"""
        info(f"搜索电影: {serial_number}")
        search_results = self._search_movie(serial_number)
        if not search_results:
            return None

        return self._fetch_movie_details(search_results[0].uri)

    def _search_movie(self, serial_number: str) -> Optional[List]:
        """搜索电影"""
        search_url = f'{self.base_url}/search?q={serial_number}&f=all'
        search_soup = self.http_util.request(url=search_url)
        return self.parser.parse_search_results(search_soup) if search_soup else None

    def _fetch_movie_details(self, uri: str) -> Optional[Movie]:
        """获取电影详情"""
        detail_url = f'{self.base_url}{uri}'
        detail_soup = self.http_util.request(url=detail_url)
        return self.parser.parse_movie_details_page(detail_soup) if detail_soup else None

    def _process_movie_data(self, movie: Movie) -> Optional[Movie]:
        """处理电影数据"""
        existing_movie = self._get_existing_movie(movie.serial_number)
        return (self._update_movie(existing_movie, movie) if existing_movie
                else self._create_movie(movie))

    def _get_existing_movie(self, serial_number: str) -> Optional[Movie]:
        """获取已存在的电影记录"""
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
        """更新电影信息"""
        self._update_movie_fields(existing_movie, new_movie)
        self._update_movie_relations(existing_movie, new_movie)
        return self.services['movie'].update(existing_movie)

    def _update_movie_fields(self, existing_movie: Movie, new_movie: Movie):
        """更新电影字段"""
        fields = ['name', 'title', 'pic_cover', 'release_date', 'length',
                 'have_mg', 'have_file', 'have_hd', 'have_sub']
        for field in fields:
            if value := getattr(new_movie, field, None):
                setattr(existing_movie, field, value)

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
            existing_movie.studio = self._get_or_create_entity(
                'studio', new_movie.studio.name)

        relations = {
            'actors': self.services['actor'],
            'directors': self.services['director'],
            'seriess': self.services['series'],
            'genres': self.services['genre'],
            'labels': self.services['label']
        }

        for rel_name, service in relations.items():
            self._update_relation(existing_movie, new_movie, rel_name, service)

    def _update_relation(self, existing_movie: Movie, new_movie: Movie,
                        rel_name: str, service):
        """更新单个关联关系"""
        existing = getattr(existing_movie, rel_name)
        existing_names = {e.name for e in existing}
        for entity in getattr(new_movie, rel_name, []):
            if entity.name not in existing_names:
                db_entity = self._get_or_create_entity(
                    rel_name.rstrip('s'), entity.name)
                existing.append(db_entity)

    def _process_movie_relations(self, movie: Movie):
        """处理新电影的关联关系"""
        if movie.studio:
            movie.studio = self._get_or_create_entity(
                'studio', movie.studio.name)

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
                db_entity = self._get_or_create_entity(
                    rel_name.rstrip('s'), entity.name)
                processed_entities.append(db_entity)
            setattr(movie, rel_name, processed_entities)

    def _get_or_create_entity(self, service_name: str, entity_name: str):
        """获取或创建实体"""
        service = self.services[service_name]
        return (service.get_by_name(entity_name) or
                service.create(service.model_class(name=entity_name)))