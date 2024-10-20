from typing import List, Optional
from bs4 import BeautifulSoup
from datetime import datetime
import json

from app.config.app_config import AppConfig
from app.model.db.movie_model import Movie, Chart, ChartEntry, ChartType, Studio
from app.model.enums import DownloadStatus
from app.services.actor_service import ActorService
from app.services.base_service import BaseService
from app.services.chart_entry_service import ChartEntryService
from app.services.chart_service import ChartService
from app.services.chart_type_service import ChartTypeService
from app.services.director_service import DirectorService
from app.services.download_service import DownloadService
from app.services.genre_service import GenreService
from app.services.label_service import LabelService
from app.services.magnet_service import MagnetService
from app.services.movie_service import MovieService
from app.services.series_service import SeriesService
from app.services.studio_service import StudioService
from app.services.cache_service import CacheService
from app.utils.http_util import HttpUtil
from app.utils.page_parser_util import PageParserUtil
from app.utils.log_util import debug, info
from app.utils.parser.parser_factory import ParserFactory


class ScraperService:
    CACHE_KEY_PREFIX = {
        'movie': 'movie:',
        'actor': 'actor:',
        'director': 'director:',
        'series': 'series:',
        'studio': 'studio:',
        'genre': 'genre:',
        'label': 'label:'
    }
    CACHE_EXPIRE_TIME = 3600 * 24  # 24小时

    def __init__(self):
        self.config = AppConfig().get_web_scraper_config()
        self.base_url = self.config.get('javdb_url', "https://javdb.com")

        # 初始化所有服务
        self.movie_service = MovieService()
        self.actor_service = ActorService()
        self.studio_service = StudioService()
        self.director_service = DirectorService()
        self.genre_service = GenreService()
        self.magnet_service = MagnetService()
        self.series_service = SeriesService()
        self.label_service = LabelService()
        self.chart_service = ChartService()
        self.chart_type_service = ChartTypeService()
        self.chart_entry_service = ChartEntryService()
        self.download_service = DownloadService()
        self.cache_service = CacheService()

        self.http_util = HttpUtil()
        self.page_parser = PageParserUtil()
        self.failed_entries = []

    def process_charts(self):
        """处理所有榜单"""
        chart_list = self.chart_service.parse_local_chartlist()
        for chart in chart_list:
            self._process_chart(chart)
        self._save_failed_entries()

    def _process_chart(self, chart: Chart):
        """处理单个榜单"""
        chart = self._process_chart_type(chart)
        for entry in chart.entries:
            entry.chart = chart
            self._process_chart_entry(entry)

    def _process_chart_type(self, chart: Chart) -> Chart:
        """处理榜单类型"""
        chart_from_db = self.chart_service.get_by_name(chart.name)
        if chart_from_db:
            chart.id = chart_from_db.id

        default_type = self.chart_type_service.get_current_chart_type()
        type_from_db = self.chart_type_service.get_by_name(default_type.name)
        chart.chart_type = type_from_db or default_type

        return chart

    def _process_related_entities(self, movie: Movie):
        """处理电影相关实体(演员、导演等)"""
        # 优先处理 Studio，因为 Movie 依赖它
        if movie.studio:
            cache_key = f"{self.CACHE_KEY_PREFIX['studio']}{movie.studio.name}"
            cached_studio = self.cache_service.get(cache_key)

            if cached_studio:
                movie.studio = Studio.from_dict(cached_studio)
            else:
                db_studio = self.studio_service.get_by_name(movie.studio.name)
                if db_studio:
                    # 合并新旧信息
                    for attr, value in vars(movie.studio).items():
                        if value and not getattr(db_studio, attr):
                            setattr(db_studio, attr, value)
                    movie.studio = db_studio
                else:
                    movie.studio = self.studio_service.create(movie.studio)
                self.cache_service.set(cache_key, movie.studio.to_dict(), self.CACHE_EXPIRE_TIME)

        # 处理其他多对多关系
        relations = {
            'actors': (self.actor_service, 'actor'),
            'directors': (self.director_service, 'director'),
            'series': (self.series_service, 'series'),
            'genres': (self.genre_service, 'genre'),
            'labels': (self.label_service, 'label')
        }

        for attr, (service, cache_type) in relations.items():
            if hasattr(movie, attr):
                entities = getattr(movie, attr)
                updated_entities = []

                for entity in entities:
                    cache_key = f"{self.CACHE_KEY_PREFIX[cache_type]}{entity.name}"
                    cached_entity = self.cache_service.get(cache_key)

                    if cached_entity:
                        updated_entities.append(ChartEntry.from_dict(cached_entity))
                    else:
                        db_entity = service.get_by_name(entity.name)
                        if db_entity:
                            # 合并信息
                            for k, v in vars(entity).items():
                                if v and not getattr(db_entity, k):
                                    setattr(db_entity, k, v)
                            entity = db_entity
                        else:
                            entity = service.create(entity)
                        if entity:
                            self.cache_service.set(cache_key, entity.to_dict(), self.CACHE_EXPIRE_TIME)
                            updated_entities.append(entity)

                setattr(movie, attr, updated_entities)

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

    def _process_movie_download(self, movie: Movie) -> int:
        """处理电影下载"""
        if not movie.have_mg or not movie.magnets:
            return DownloadStatus.NO_SOURCE.value

        status = self.download_service.get_download_status(movie.serial_number)
        if status in [DownloadStatus.DOWNLOADED.value, DownloadStatus.IN_LIBRARY.value]:
            return status

        if not status or status <= DownloadStatus.DOWNLOADING.value:
            magnet = movie.magnets[0]
            if status == DownloadStatus.DOWNLOADING.value:
                if not self.download_service.check_download_speed(movie.serial_number):
                    magnet = self.download_service.get_next_magnet(movie.serial_number, movie.magnets)

            if self.download_service.add_torrent(f"magnet:?xt=urn:btih:{magnet.magnet_xt}"):
                return DownloadStatus.DOWNLOADING.value

        return DownloadStatus.DOWNLOAD_FAILED.value

    def _get_movie_info(self, chart_entry: ChartEntry) -> Optional[Movie]:
        """获取电影信息"""
        cache_key = f"{self.CACHE_KEY_PREFIX['movie']}{chart_entry.serial_number}"
        cached_movie = self.cache_service.get(cache_key)
        if cached_movie:
            return Movie.from_dict(cached_movie)

        url = self._get_movie_page_url(chart_entry)
        soup = self.http_util.request(url=url, proxy_enable=self.config["proxy_enable"])
        if soup:
            movie = self.extract_movie_details_page(soup)
            if movie:
                self.cache_service.set(cache_key, movie.to_dict(), self.CACHE_EXPIRE_TIME)
                return movie
        return None

    def _process_chart_entry(self, chart_entry: ChartEntry):
        """处理榜单条目"""
        # 1. 获取电影信息
        parsed_movie = self._get_movie_info(chart_entry)
        if not parsed_movie:
            self.failed_entries.append({
                'serial_number': chart_entry.serial_number,
                'chart_name': chart_entry.chart.name,
                'error': 'Failed to parse movie info'
            })
            return

        # 2. 处理关联实体
        self._process_related_entities(parsed_movie)

        # 3. 处理电影信息
        movie_from_db = self.movie_service.get_movie_from_db_by_serial_number(
            chart_entry.serial_number)

        if movie_from_db:
            movie = self._process_movie_info(movie_from_db, parsed_movie)
        else:
            movie = parsed_movie
            movie.download_status = DownloadStatus.CRAWLED.value

        # 4. 处理下载
        movie.download_status = self._process_movie_download(movie)

        # 5. 更新电影和榜单条目
        #movie = self.movie_service.save(movie)
        chart_entry.movie = movie

        # 6. 处理榜单条目
        if chart_entry.chart.id and movie.id:
            existing_entry = self.chart_entry_service.get_chart_entry_by_movie_id_and_chart_id(
                movie.id, chart_entry.chart.id)
            if existing_entry:
                existing_entry.rank = chart_entry.rank
                existing_entry.score = chart_entry.score
                existing_entry.votes = chart_entry.votes
                self.chart_entry_service.update(existing_entry)
                return

        self.chart_entry_service.create(chart_entry)

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
        parser = ParserFactory.get_parser()
        results = parser.parse_search_results(soup)
        return results[0].uri if results else None

    def extract_movie_details_page(self, soup: BeautifulSoup) -> Optional[Movie]:
        """从电影详情页提取电影信息"""
        parser = ParserFactory.get_parser()
        return parser.parse_movie_details_page(soup)

    def _save_failed_entries(self):
        """保存处理失败的条目"""
        if not self.failed_entries:
            return

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"failed_entries_{timestamp}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.failed_entries, f, ensure_ascii=False, indent=2)