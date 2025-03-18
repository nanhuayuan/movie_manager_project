import time
import random
import urllib
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import joinedload
from sqlalchemy.exc import IntegrityError

from app.model.db.movie_model import Movie, Chart, ChartEntry, ChartType, Actor
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
        self.actor_search_uri = config.get('javdb_actor_search_uri', "/search?q=%s&f=actor")
        self.cookie = config.get('cookie')
        logger.info(f"初始化ScraperService，基础URL: {self.base_url}")

        # 获取配置
        chart_config = AppConfig().get_chart_config()
        self.chart_content = chart_config.get('chart_content', {})
        self.entity_type = self.chart_content.get('entity_type', 'movie')
        self.actor_min_evaluations = int(self.chart_content.get('actor_min_evaluations', 200))
        self.actor_sort_type = int(self.chart_content.get('actor_sort_type', 4))
        logger.info(f"演员电影配置: 最低评价人数={self.actor_min_evaluations}, 排序方式={self.actor_sort_type}")

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
                # 根据条目类型选择处理方法
                if self.entity_type == 'actor':
                    logger.info(f"处理演员条目: {entry.name}")
                    entry.entity_type = self.entity_type
                    entry.name = entry.serial_number
                    self._process_actor_entry(entry, chart.name)
                else:  # 默认为电影类型
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
                self.service_map['chart_entry'].update(existing_entry)

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

            magnet = movie.magnets[0]
            magnet_link = f"magnet:?xt=urn:btih:{magnet.magnet_xt}"

            status = self.service_map['download'].get_download_status(name = movie.serial_number,hash=magnet)
            logger.debug(f"当前下载状态: {status}")

            # 已完成状态直接返回
            if status in [DownloadStatus.COMPLETED.value, DownloadStatus.IN_LIBRARY.value]:
                logger.info(f"电影下载状态已完成: {movie.serial_number}")
                return status
            elif status <= DownloadStatus.COMPLETED.value and status >= DownloadStatus.QUEUED.value:
                logger.info(f"电影正在下载中: {movie.serial_number}")
                return status
            # 添加下载任务
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

    # actor start
    def _process_actor_entry(self, entry: ChartEntry, chart_name: str):
        """处理演员类型的榜单条目"""
        actor_name = entry.name
        logger.info(f"开始处理演员榜单条目: {actor_name}")

        # 搜索演员
        actor_info = self._search_actor(actor_name)
        if not actor_info:
            logger.warning(f"未找到演员信息: {actor_name}")
            return

        #  TODO 获得演员详情信息


        # 获取或创建演员记录
        actor = self._get_or_create_actor(actor_info)
        if not actor:
            logger.warning(f"无法创建演员记录: {actor_name}")
            return

        # 保存演员榜单条目
        self._save_actor_chart_entry(entry, actor, chart_name)

        # 获取演员的合格电影
        eligible_movies = self._get_eligible_movies_for_actor(actor)
        if not eligible_movies:
            logger.info(f"演员 {actor_name} 没有符合条件的电影")
            return

        # 处理每部电影
        logger.info(f"演员 {actor_name} 有 {len(eligible_movies)} 部符合条件的电影")
        processed_movies = []
        for movie_info in eligible_movies:
            try:
                if movie_info['code'].startswith('FC2'):
                    logger.info(f"跳过FC2类型电影: {movie_info['code']}")
                    continue

                # 创建电影ChartEntry
                movie_entry = ChartEntry()
                movie_entry.entity_type = 'movie'
                movie_entry.serial_number = movie_info['code']
                movie_entry.name = movie_info['title']
                movie_entry.uri = movie_info['uri']

                # 处理电影
                if movie := self._fetch_and_process_movie(movie_entry):
                    processed_movies.append(movie)
                    logger.info(f"成功处理电影: {movie_info['code']}")

                time.sleep(random.randint(1, 5))
            except Exception as e:
                logger.error(f"处理演员电影时出错: {str(e)}")

        logger.info(f"演员 {actor_name} 处理完成，成功处理 {len(processed_movies)} 部电影")

    def _search_actor(self, actor_name: str) -> Dict[str, Any]:
        """搜索演员信息"""
        search_url = f"{self.base_url}{self.actor_search_uri % urllib.parse.quote(actor_name)}"
        logger.info(f"搜索演员URL: {search_url}")

        search_page = self.http_util.request(url=search_url,cookie=self.cookie)
        if not search_page:
            logger.warning(f"获取演员搜索页面失败: {search_url}")
            return None

        # 解析演员搜索结果
        # 注意：这里假设有一个parse_actor_search_results方法，实际情况可能需要调整
        actor_results = self.parser.parse_actor_search_results(search_page)
        if not actor_results or len(actor_results) == 0:
            logger.warning(f"未找到演员: {actor_name}")
            return None

        # 如果找到多个演员，可能需要进一步处理
        if len(actor_results) > 1:
            logger.info(f"找到多个演员信息，使用第一个结果: {actor_name}")

        return actor_results[0]

    def _get_or_create_actor(self, actor_info: Dict[str, Any]) -> Optional[Actor]:
        """获取或创建演员记录"""
        if not actor_info or 'name' not in actor_info:
            logger.error("演员信息不完整")
            return None

        actor_name = actor_info.get('name')
        actor_uri = actor_info.get('uri')

        # 先尝试从数据库获取
        actor = self.service_map['actor'].get_by_name(actor_name)
        if actor:
            logger.info(f"找到现有演员记录: {actor_name}")
            return actor

        # 创建新演员记录
        new_actor = Actor()
        new_actor.name = actor_name
        new_actor.uri = actor_uri

        # 如果有其他信息也可以设置
        if 'photo' in actor_info:
            new_actor.photo = actor_info['photo']

        try:
            actor = self.service_map['actor'].create(new_actor)
            logger.info(f"创建新演员记录: {actor_name}")
            return actor
        except IntegrityError:
            logger.warning(f"创建演员记录时遇到完整性错误，尝试获取已存在记录: {actor_name}")
            return self.service_map['actor'].get_by_name(actor_name)
        except Exception as e:
            logger.error(f"创建演员记录失败: {str(e)}")
            return None

    def _save_actor_chart_entry(self, entry: ChartEntry, actor: Actor, chart_name: str):
        """保存演员榜单条目"""
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

        # 检查是否已存在该演员的条目
        existing_entry = self.service_map['chart_entry'].get_by_chart_and_actor(db_chart.id, actor.id)

        if not existing_entry:
            # 创建新条目
            entry.actor = actor
            entry.chart = db_chart
            entry.entity_type = 'actor'
            self.service_map['chart_entry'].create(entry)
            logger.info(f"创建新的演员榜单条目: {actor.name}")
        else:
            # 更新现有条目
            if not existing_entry.actor or existing_entry.actor.id != actor.id:
                existing_entry.actor = actor
                self.service_map['chart_entry'].update(existing_entry)
                logger.info(f"更新演员榜单条目: {actor.name}")

    def _get_eligible_movies_for_actor(self, actor: Actor) -> List[Dict[str, Any]]:
        """获取演员的合格电影"""
        if not actor.uri:
            logger.warning(f"演员 {actor.name} 没有URI")
            return []

        actor_url = f"{self.base_url}{actor.uri}"
        logger.info(f"获取演员页面: {actor_url}")

        # 获取演员页面
        actor_page = self.http_util.request(url=actor_url)
        if not actor_page:
            logger.warning(f"获取演员页面失败: {actor_url}")
            return []

        # 解析演员页面获取电影总数和最大页数
        movie_count, max_page = self._parse_actor_page_info(actor_page)
        if movie_count <= 0:
            logger.info(f"演员 {actor.name} 没有电影")
            return []

        logger.info(f"演员 {actor.name} 共有 {movie_count} 部电影，最大页数: {max_page}")

        # 获取所有符合条件的电影
        eligible_movies = []
        current_page = 1

        while current_page <= max_page:
            page_url = f"{self.base_url}{actor.uri}?page={current_page}&sort_type={self.actor_sort_type}"
            logger.info(f"获取演员电影页面 {current_page}/{max_page}: {page_url}")

            page_content = self.http_util.request(url=page_url)
            if not page_content:
                logger.warning(f"获取演员电影页面失败: {page_url}")
                current_page += 1
                continue

            # 解析页面获取电影列表
            page_movies = self._parse_actor_movies_page(page_content)
            if page_movies:
                eligible_movies.extend(page_movies)

            current_page += 1
            time.sleep(random.randint(1, 5))

        logger.info(f"演员 {actor.name} 共获取到 {len(eligible_movies)} 部符合条件的电影")
        return eligible_movies

    def _parse_actor_page_info(self, page_content: str) -> tuple:
        """解析演员页面信息，获取电影数量和最大页数"""
        try:
            return self.parser.parse_actor_page_info(page_content)
        except Exception as e:
            logger.error(f"解析演员页面信息失败: {str(e)}")
            return 0, 0

    def _parse_actor_movies_page(self, page_content: str) -> list:
        """解析演员电影页面，返回符合条件的电影列表"""
        try:
            movies = self.parser.parse_actor_movies_page(page_content,
                                                         min_evaluations=self.actor_min_evaluations)
            return movies if movies else []
        except Exception as e:
            logger.error(f"解析演员电影页面失败: {str(e)}")
            return []