import time
import random
from typing import Optional, List
from sqlalchemy.orm import joinedload
from sqlalchemy.exc import IntegrityError

from app.model.db.movie_model import Movie, Chart, ChartEntry, ChartType
from app.services import (
    MovieService, ActorService, StudioService, DirectorService,
    GenreService, SeriesService, LabelService, ChartService,
    ChartTypeService, ChartEntryService, MagnetService, DownloadService, EverythingService, JellyfinService
)
from app.services.download_failure_service import DownloadFailureService
from app.utils.download_client import DownloadStatus
from app.utils.http_util import HttpUtil
from app.utils.parser.parser_factory import ParserFactory
from app.config.log_config import info, error
from app.config.log_config import LogUtil
from app.config.app_config import AppConfig

logger = LogUtil.get_logger()


class ScraperService:
    """电影数据抓取与处理服务"""

    def __init__(self):
        config = AppConfig().get_web_scraper_config()
        self.base_url = config.get('javdb_url', "https://javdb.com")
        logger.info(f"初始化ScraperService，基础URL: {self.base_url}")

        # 初始化服务
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
            'download_failure': DownloadFailureService(),
            'jellyfin': JellyfinService()
        }
        logger.info(f"已初始化 {len(self.service_map)} 个服务")

        self.http_util = HttpUtil()
        self.parser = ParserFactory.get_parser()
        logger.info("HTTP工具和解析器已准备就绪")

    def process_all_charts(self):
        """处理所有榜单数据"""
        try:
            logger.info("开始处理所有榜单数据")
            if not (charts := self.service_map['chart'].parse_local_chartlist()):
                logger.warning("未找到任何榜单数据")
                return

            logger.info(f"找到 {len(charts)} 个榜单")
            for chart in charts:
                self._process_chart(chart)
            logger.info("所有榜单处理完成")
        except Exception as e:
            logger.error(f"榜单处理全局错误: {str(e)}")
            raise

    def _process_chart(self, chart: Chart):
        """处理单个榜单数据"""
        logger.info(f"开始处理榜单: {chart.name}")

        chart_entries = list(chart.entries)
        logger.info(f"榜单 '{chart.name}' 共有 {len(chart_entries)} 个条目")
        for entry in chart_entries:
            try:
                if entry.serial_number and entry.serial_number.startswith('FC2'):
                    logger.info(f"跳过FC2类型条目: {entry.serial_number}")
                    continue

                logger.debug(f"处理条目: {entry.serial_number},榜单: {chart.name}，排行: {entry.rank}/{len(chart_entries)}")
                if movie := self._fetch_and_process_movie(entry):
                    self._save_chart_entry(entry, movie, chart.name)
                    logger.info(f"成功处理并保存条目: {entry.serial_number}")
                else:
                    logger.warning(f"无法处理条目: {entry.serial_number}")

                time.sleep(random.randint(1, 5))
            except Exception as e:
                logger.error(f"处理榜单 '{chart.name}' 时出错: {str(e)}")
        logger.info(f"榜单 '{chart.name}' 处理完成")


    def _fetch_and_process_movie(self, entry: ChartEntry) -> Optional[Movie]:
        """获取并处理电影信息"""
        logger.info(f"开始获取电影信息: {entry.serial_number}")

        if not (movie_info := self._fetch_movie_info(entry)):
            logger.warning(f"未能获取电影详情: {entry.serial_number}")
            return None

        if not movie_info.serial_number:
            logger.warning(f"电影 {entry.serial_number} 的序列号未设置")
            raise Exception(f"电影 {entry.serial_number} 的序列号未设置")

        # 处理下载状态
        movie_info.download_status = self._process_movie_download(movie=movie_info)
        logger.debug(f"电影信息详情: {movie_info.to_dict()}")

        existing_movie = self._get_existing_movie(entry.serial_number)
        result = (
            self._update_movie(existing_movie, movie_info)
            if existing_movie
            else self._create_new_movie(movie_info)
        )

        if result:
            logger.info(f"电影处理成功: {entry.serial_number}")
        return result

    def _fetch_movie_info(self, entry: ChartEntry) -> Optional[dict]:
        """获取电影详细信息。"""
        uri = self._get_movie_detail_page_url(entry)
        if not uri:
            logger.warning(f"未找到电影 {entry.serial_number} 的详情页URL")
            return None

        detail_url = f'{self.base_url}{uri}'
        logger.debug(f"电影详情页URL: {detail_url}")

        if not (detail_page := self.http_util.request(url=detail_url)):
            logger.warning(f"获取电影详情页失败: {detail_url}")
            return None

        movie_details = self.parser.parse_movie_details_page(detail_page)

        if movie_details.serial_number and movie_details.serial_number.startswith('FC2'):
            logger.info(f"跳过FC2类型条目: {movie_details.serial_number}")
            return None

        if not movie_details:
            logger.warning(f"解析电影详情页失败: {detail_url}")
        return movie_details

    def _get_movie_detail_page_url(self, entry: ChartEntry) -> str:
        """获取电影详情页URL。"""
        logger.debug(f"获取电影 {entry.serial_number} 的详情页URL")

        if entry.uri:
            logger.debug(f"使用预设URI: {entry.uri}")
            return entry.uri

        # 没有地址要去搜索
        search_url = f'{self.base_url}/search?q={entry.serial_number}&f=all'
        logger.debug(f"搜索URL: {search_url}")

        if not (search_page := self.http_util.request(url=search_url)):
            logger.warning(f"搜索页面请求失败: {search_url}")
            return None

        if not (search_results := self.parser.parse_search_results(search_page)):
            logger.warning(f"搜索结果解析失败: {search_url}")
            # raise Exception(f"搜索失败，查找不到: {entry.serial_number}")
            return None

        # 搜索结果判断逻辑
        if entry.serial_number.lower() != search_results[0].serial_number.lower():
            logger.warn(f"搜索失败，查找到: '{search_results[0].serial_number}'，但输入为: '{entry.serial_number}'")

        if entry.serial_number and entry.serial_number.startswith('FC2'):
            raise Exception(f"搜索失败，查找到FC2: '{search_results[0].serial_number}'，但输入为:'{entry.serial_number}'")
        uri = search_results[0].uri
        logger.debug(f"找到搜索结果URI: {uri}")
        return uri

    def _get_existing_movie(self, serial_number: str) -> Optional[Movie]:
        """从数据库获取已存在的电影信息"""
        logger.debug(f"查询电影是否已存在: {serial_number}")
        return self.service_map['movie'].get_movie_from_db_by_serial_number(
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

    def _create_new_movie(self, movie: Movie) -> Optional[Movie]:
        """创建新电影记录"""
        logger.info(f"创建新电影记录: {movie.serial_number}")
        self._process_all_relations(movie)
        logger.debug(f"创建前电影信息详情: {movie.to_dict()}")

        try:
            new_movie = self.service_map['movie'].create(movie)
            logger.info(f"新电影记录创建成功: {new_movie.serial_number}")
            return new_movie
        except IntegrityError:
            logger.warning(f"创建电影记录时遇到完整性错误，尝试获取已存在记录: {movie.serial_number}")
            return self.service_map['movie'].get_movie_from_db_by_serial_number(
                movie.serial_number)

    def _clean_entity_relationships(self, entity) -> None:
        """清理实体的关系属性，避免级联创建"""
        try:
            # 获取实体的所有属性
            relationships = ['movies', 'actors', 'directors', 'genres', 'labels', 'seriess']
            for rel in relationships:
                if hasattr(entity, rel):
                    setattr(entity, rel, [])
        except Exception as e:
            logger.error(f"清理实体关系时出错: {str(e)}")

    def _get_or_create_entity(self, entity, service_key: str):
        """获取或创建实体，确保清理关系"""
        if not entity:
            return None

        self._clean_entity_relationships(entity)
        return (
                self.service_map[service_key].get_by_name(entity.name) or
                self.service_map[service_key].create(entity)
        )

    def _process_all_relations(self, movie: Movie):
        """处理所有关联实体，避免级联创建"""
        # 处理一对多关系（制片商）
        if studio := getattr(movie, 'studio', None):
            movie.studio = self._get_or_create_entity(studio, 'studio')

        # 处理多对多关系
        relation_map = {
            'actors': 'actor',
            'directors': 'director',
            'seriess': 'series',
            'genres': 'genre',
            'labels': 'label',
            'magnets': 'magnet'
        }

        for attr, service_key in relation_map.items():
            if not hasattr(movie, attr):
                continue

            new_entities = []
            for entity in getattr(movie, attr, []):
                if db_entity := self._get_or_create_entity(entity, service_key):
                    new_entities.append(db_entity)
            setattr(movie, attr, new_entities)

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
        self._update_relations(existing, new)
        return self.service_map['movie'].update(existing)

    def _update_relations(self, existing: Movie, new: Movie):
        """更新电影的关联实体"""
        # 更新制片商
        if new_studio := getattr(new, 'studio', None):
            existing.studio = self._get_or_create_entity(new_studio, 'studio')

        # 更新多对多关系
        relation_map = {
            'actors': 'actor',
            'directors': 'director',
            'seriess': 'series',
            'genres': 'genre',
            'labels': 'label',
            'magnets': 'magnet'
        }

        for attr, service_key in relation_map.items():
            if not hasattr(new, attr):
                continue

            existing_entities = getattr(existing, attr)
            existing_names = {e.name for e in existing_entities}

            for new_entity in getattr(new, attr, []):
                if new_entity.name not in existing_names:
                    if db_entity := self._get_or_create_entity(new_entity, service_key):
                        existing_entities.append(db_entity)

    def _save_chart_entry(self, entry: ChartEntry, movie: Movie, chart_name: str):
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
            logger.debug(f"开始处理电影下载状态: {movie.serial_number}")

            if self.service_map['jellyfin'].check_movie_exists(title=movie.serial_number):
                logger.info(f"电影已存在于Jellyfin库: {movie.serial_number}")
                return DownloadStatus.IN_LIBRARY.value

            elif self.service_map['everything'].local_exists_movie(movie.serial_number):
                logger.info(f"本地已存在电影: {movie.serial_number}")
                return DownloadStatus.COMPLETED.value

            if not movie.have_mg or not movie.magnets:
                logger.warning(f"电影无可用磁力链接: {movie.serial_number}")
                return DownloadStatus.NO_SOURCE.value

            status = self.service_map['download'].get_download_status(movie.serial_number)
            logger.debug(f"当前下载状态: {status}")

            # 已完成状态直接返回
            if status in [DownloadStatus.COMPLETED.value, DownloadStatus.IN_LIBRARY.value]:
                logger.info(f"电影下载状态已完成: {movie.serial_number}")
                return status

            # 添加下载任务
            magnet = movie.magnets[0]
            magnet_link = f"magnet:?xt=urn:btih:{magnet.magnet_xt}"
            logger.info(f"准备添加下载任务: {magnet_link}")

            if self.service_map['download'].add_download(magnet_link):
                logger.info(f"下载任务添加成功: {movie.serial_number}")
                return DownloadStatus.DOWNLOADING.value

            logger.warning(f"下载任务添加失败: {movie.serial_number},记录到待下载表")
            self.service_map['download_failure'].add_download_failed(movie)
            return DownloadStatus.DOWNLOAD_FAILED.value
        except Exception as e:
            logger.error(f"处理电影下载状态时发生错误：{e}")
            return DownloadStatus.ERROR.value
