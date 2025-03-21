import time
import random
import urllib
from datetime import datetime
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
from app.config.log_config import debug, info, warning, error, critical
from app.config.log_config import LogUtil
from app.config.app_config import AppConfig

logger = LogUtil.get_logger()


class ScraperService:
    """电影数据抓取与处理服务"""

    def __init__(self):
        config = AppConfig().get_web_scraper_config()
        self.scraper_from = config.get('from', 'javdb')
        self.scraper_web_config = config.get(self.scraper_from)
        self.base_url = self.scraper_web_config.get('domain', "https://javdb.com")
        self.actor_search_uri = self.scraper_web_config.get('actor_search_uri', "/search?q=%s&f=actor")
        self.actor_detail_uri = self.scraper_web_config.get('actor_detail_uri', "%s")  # 添加演员详情URI配置
        self.cookie = self.scraper_web_config.get('cookie')
        info(f"初始化ScraperService，基础URL: {self.base_url}")

        # 获取配置
        chart_config = AppConfig().get_chart_config()
        self.chart_content = chart_config.get('chart_content', {})
        self.entity_type = self.chart_content.get('entity_type', 'movie')
        self.actor_min_evaluations = int(self.chart_content.get('actor_min_evaluations', 200))
        self.actor_sort_type = int(self.chart_content.get('actor_sort_type', 4))
        info(f"演员电影配置: 最低评价人数={self.actor_min_evaluations}, 排序方式={self.actor_sort_type}")

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
        info(f"已初始化 {len(self.service_map)} 个服务")

        self.http_util = HttpUtil()
        self.parser = ParserFactory.get_parser()
        info("HTTP工具和解析器已准备就绪")

    def process_all_charts(self):
        """处理所有榜单数据"""
        try:
            info("开始处理所有榜单数据")
            if not (charts := self.service_map['chart'].parse_local_chartlist()):
                warning("未找到任何榜单数据")
                return

            info(f"找到 {len(charts)} 个榜单")
            for chart in charts:
                self._process_chart(chart)
            info("所有榜单处理完成")
        except Exception as e:
            error(f"榜单处理全局错误: {str(e)}")
            raise

    def _process_chart(self, chart: Chart):
        """处理单个榜单数据"""
        info(f"开始处理榜单: {chart.name}")

        chart_entries = list(chart.entries)
        info(f"榜单 '{chart.name}' 共有 {len(chart_entries)} 个条目")
        for entry in chart_entries:
            try:
                # 根据条目类型选择处理方法
                if self.entity_type == 'actor':
                    entry.entity_type = self.entity_type
                    entry.name = entry.serial_number
                    info(f"处理演员条目: {entry.name}")
                    self._process_actor_entry(entry, chart.name)
                else:  # 默认为电影类型
                    if entry.serial_number and entry.serial_number.startswith('FC2'):
                        info(f"跳过FC2类型条目: {entry.serial_number}")
                        continue

                    debug(f"处理条目: {entry.serial_number},榜单: {chart.name}，排行: {entry.rank}/{len(chart_entries)}")
                    if movie := self._fetch_and_process_movie(entry):
                        self._save_chart_entry(entry, movie, chart.name)
                        info(f"成功处理并保存条目: {entry.serial_number}")
                    else:
                        warning(f"无法处理条目: {entry.serial_number}")

                time.sleep(random.randint(1, 5))
            except Exception as e:
                error(f"处理榜单 '{chart.name}' 时出错: {str(e)}")
        info(f"榜单 '{chart.name}' 处理完成")

    def _fetch_and_process_movie(self, entry: ChartEntry) -> Optional[Movie]:
        """获取并处理电影信息"""
        info(f"开始获取电影信息: {entry.serial_number}")

        if not (movie_info := self._fetch_movie_info(entry)):
            warning(f"未能获取电影详情: {entry.serial_number}")
            return None

        if not movie_info.serial_number:
            warning(f"电影 {entry.serial_number} 的序列号未设置")
            raise Exception(f"电影 {entry.serial_number} 的序列号未设置")

        # 处理下载状态
        movie_info.download_status = self._process_movie_download(movie=movie_info)
        debug(f"电影信息详情: {movie_info.to_dict()}")

        existing_movie = self._get_existing_movie(entry.serial_number)
        result = (
            self._update_movie(existing_movie, movie_info)
            if existing_movie
            else self._create_new_movie(movie_info)
        )

        if result:
            info(f"电影处理成功: {entry.serial_number}")
        return result

    def _fetch_movie_info(self, entry: ChartEntry) -> Optional[dict]:
        """获取电影详细信息。"""
        uri = self._get_movie_detail_page_url(entry)
        if not uri:
            warning(f"未找到电影 {entry.serial_number} 的详情页URL")
            return None

        detail_url = f'{self.base_url}{uri}'
        debug(f"电影详情页URL: {detail_url}")

        if not (detail_page := self.http_util.request(url=detail_url)):
            warning(f"获取电影详情页失败: {detail_url}")
            return None

        movie_details = self.parser.parse_movie_details_page(detail_page)

        if movie_details.serial_number and movie_details.serial_number.startswith('FC2'):
            info(f"跳过FC2类型条目: {movie_details.serial_number}")
            return None

        if not movie_details:
            warning(f"解析电影详情页失败: {detail_url}")
        return movie_details

    def _get_movie_detail_page_url(self, entry: ChartEntry) -> str:
        """获取电影详情页URL。"""
        debug(f"获取电影 {entry.serial_number} 的详情页URL")

        if entry.uri:
            debug(f"使用预设URI: {entry.uri}")
            return entry.uri

        # 没有地址要去搜索
        search_url = f'{self.base_url}/search?q={entry.serial_number}&f=all'
        debug(f"搜索URL: {search_url}")

        if not (search_page := self.http_util.request(url=search_url)):
            warning(f"搜索页面请求失败: {search_url}")
            return None

        if not (search_results := self.parser.parse_search_results(search_page)):
            warning(f"搜索结果解析失败: {search_url}")
            # raise Exception(f"搜索失败，查找不到: {entry.serial_number}")
            return None

        # 搜索结果判断逻辑
        if entry.serial_number.lower() != search_results[0].serial_number.lower():
            warning(f"搜索失败，查找到: '{search_results[0].serial_number}'，但输入为: '{entry.serial_number}'")

        if entry.serial_number and entry.serial_number.startswith('FC2'):
            raise Exception(f"搜索失败，查找到FC2: '{search_results[0].serial_number}'，但输入为:'{entry.serial_number}'")
        uri = search_results[0].uri
        debug(f"找到搜索结果URI: {uri}")
        return uri

    def _get_existing_movie(self, serial_number: str) -> Optional[Movie]:
        """从数据库获取已存在的电影信息"""
        debug(f"查询电影是否已存在: {serial_number}")
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
        info(f"创建新电影记录: {movie.serial_number}")
        self._process_all_relations(movie)
        debug(f"创建前电影信息详情: {movie.to_dict()}")

        try:
            new_movie = self.service_map['movie'].create(movie)
            info(f"新电影记录创建成功: {new_movie.serial_number}")
            return new_movie
        except IntegrityError:
            warning(f"创建电影记录时遇到完整性错误，尝试获取已存在记录: {movie.serial_number}")
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
            error(f"清理实体关系时出错: {str(e)}")

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
            debug(f"开始处理电影下载状态: {movie.serial_number}")

            if self.service_map['jellyfin'].check_movie_exists(title=movie.serial_number):
                info(f"电影已存在于Jellyfin库: {movie.serial_number}")
                return DownloadStatus.IN_LIBRARY.value

            elif self.service_map['everything'].local_exists_movie(movie.serial_number):
                info(f"本地已存在电影: {movie.serial_number}")
                return DownloadStatus.COMPLETED.value

            if not movie.have_mg or not movie.magnets:
                warning(f"电影无可用磁力链接: {movie.serial_number}")
                return DownloadStatus.NO_SOURCE.value

            magnet = movie.magnets[0]
            magnet_link = f"magnet:?xt=urn:btih:{magnet.magnet_xt}"

            status = self.service_map['download'].get_download_status(name = movie.serial_number,hash=magnet)
            debug(f"当前下载状态: {status}")

            # 已完成状态直接返回
            if status in [DownloadStatus.COMPLETED.value, DownloadStatus.IN_LIBRARY.value]:
                info(f"电影下载状态已完成: {movie.serial_number}")
                return status
            elif status <= DownloadStatus.COMPLETED.value and status >= DownloadStatus.QUEUED.value:
                info(f"电影正在下载中: {movie.serial_number}")
                return status
            # 添加下载任务
            info(f"准备添加下载任务: {magnet_link}")

            if self.service_map['download'].add_download(magnet_link):
                info(f"下载任务添加成功: {movie.serial_number}")
                return DownloadStatus.DOWNLOADING.value

            warning(f"下载任务添加失败: {movie.serial_number},记录到待下载表")
            self.service_map['download_failure'].add_download_failed(movie)
            return DownloadStatus.DOWNLOAD_FAILED.value
        except Exception as e:
            error(f"处理电影下载状态时发生错误：{e}")
            return DownloadStatus.ERROR.value

    # actor start
    def _process_actor_entry(self, entry: ChartEntry, chart_name: str):
        """处理演员类型的榜单条目"""
        actor_name = entry.name
        info(f"开始处理演员榜单条目: {actor_name}")

        # 搜索演员
        actor_info = self._search_actor(actor_name)
        if not actor_info:
            warning(f"未找到演员信息: {actor_name}")
            return

        # 获取演员详情信息 javdb没有演员详情页
        actor_details = self._get_actor_details(actor_info.get('uri', ''))

        # 合并演员基本信息和详情信息
        actor_info.update(actor_details)

        # 获取或创建演员记录
        actor = self._get_or_create_actor(actor_info)
        if not actor:
            warning(f"无法创建演员记录: {actor_name}")
            return

        # 保存演员榜单条目
        self._save_actor_chart_entry(entry, actor, chart_name)

        # 获取演员的合格电影
        eligible_movies = self._get_eligible_movies_for_actor(actor)
        if not eligible_movies:
            info(f"演员 {actor_name} 没有符合条件的电影")
            return

        # 处理每部电影
        info(f"演员 {actor_name} 有 {len(eligible_movies)} 部符合条件的电影")
        processed_movies = []
        for movie_info in eligible_movies:
            try:
                if movie_info['code'].startswith('FC2'):
                    info(f"跳过FC2类型电影: {movie_info['code']}")
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
                    info(f"成功处理电影: {movie_info['code']}")

                time.sleep(random.randint(1, 5))
            except Exception as e:
                error(f"处理演员电影时出错: {str(e)}")

        info(f"演员 {actor_name} 处理完成，成功处理 {len(processed_movies)} 部电影")

    def _search_actor(self, actor_name: str) -> Dict[str, Any]:
        """搜索演员信息"""
        search_url = f"{self.base_url}{self.actor_search_uri % urllib.parse.quote(actor_name)}"
        info(f"搜索演员URL: {search_url}")

        search_page = self.http_util.request(url=search_url,cookie=self.cookie)
        if not search_page:
            warning(f"获取演员搜索页面失败: {search_url}")
            return None

        # 解析演员搜索结果
        actor_results = self.parser.parse_actor_search_results(search_page)
        if not actor_results or len(actor_results) == 0:
            warning(f"未找到演员: {actor_name}")
            return None

        # 如果找到多个演员，可能需要进一步处理
        if len(actor_results) > 1:
            info(f"找到｛len（actor_results）｝个演员信息，使用第一个结果: {actor_name}")

        return actor_results[0]

    def _get_or_create_actor(self, actor_info: Dict[str, Any]) -> Optional[Actor]:
        """获取或创建演员记录"""
        if not actor_info or 'name' not in actor_info:
            error("演员信息不完整")
            return None

        actor_name = actor_info.get('name')

        # 先尝试从数据库获取
        actor = self.service_map['actor'].get_by_name(actor_name)
        if actor:
            info(f"找到现有演员记录: {actor_name}")
            # 更新演员信息
            self.service_map['actor'].update_actor_info(actor, actor_info)
            return actor

        # 创建新演员记录
        new_actor = Actor()
        new_actor.name = actor_name

        # 设置详细信息
        self.service_map['actor'].set_actor_details(new_actor, actor_info)

        try:
            actor = self.service_map['actor'].create(new_actor)
            info(f"创建新演员记录: {actor_name}")
            return actor
        except IntegrityError:
            warning(f"创建演员记录时遇到完整性错误，尝试获取已存在记录: {actor_name}")
            return self.service_map['actor'].get_by_name(actor_name)
        except Exception as e:
            error(f"创建演员记录失败: {str(e)}")
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
            info(f"创建新的演员榜单条目: {actor.name}")
        else:
            # 更新现有条目
            if not existing_entry.actor or existing_entry.actor.id != actor.id:
                existing_entry.actor = actor
                self.service_map['chart_entry'].update(existing_entry)
                info(f"更新演员榜单条目: {actor.name}")

    def _get_eligible_movies_for_actor(self, actor: Actor) -> List[Dict[str, Any]]:
        """获取演员的合格电影"""
        # 根据不同来源构建演员URL
        if self.scraper_from == 'javdb':
            actor_url = f"{self.base_url}{actor.javdb_uri}"
        elif self.scraper_from == 'javbus':
            actor_url = f"{self.base_url}{actor.javbus_uri}"
        else:
            actor_url = f"{self.base_url}{actor.javlib_uri}"

        if not actor_url:
            warning(f"演员 {actor.name} 没有URI")
            return []
        info(f"获取演员页面: {actor_url}")

        # 获取演员页面
        actor_page = self.http_util.request(url=actor_url, cookie=self.cookie)
        if not actor_page:
            warning(f"获取演员页面失败: {actor_url}")
            return []

        # 解析演员页面获取电影总数和最大页数
        movie_count, max_page = self._parse_actor_page_info(actor_page)
        if movie_count <= 0:
            info(f"演员 {actor.name} 没有电影")
            return []

        info(f"演员 {actor.name} 共有 {movie_count} 部电影，最大页数: {max_page}")

        # 获取筛选条件
        movie_filters = self.scraper_web_config.get('movie_filters', {})
        min_evaluations = int(movie_filters.get('min_evaluations', 200))
        min_score = float(movie_filters.get('min_score', 0.0))
        consecutive_failures_limit = int(movie_filters.get('consecutive_failures', 5))

        # 获取所有符合条件的电影
        eligible_movies = []
        current_page = 1
        consecutive_failures = 0

        while current_page <= max_page and consecutive_failures < consecutive_failures_limit:
            # 根据不同来源构建分页URL
            page_url = self._build_actor_movies_page_url(actor, current_page)
            info(f"获取演员电影页面 {current_page}/{max_page}: {page_url}")

            page_content = self.http_util.request(url=page_url, cookie=self.cookie)
            if not page_content:
                warning(f"获取演员电影页面失败: {page_url}")
                current_page += 1
                continue

            # 解析页面获取电影列表
            page_movies = self.parser.parse_actor_movies_page(page_content)

            # 应用筛选条件
            page_eligible_movies = []
            page_failures = 0

            for movie in page_movies:
                # 检查电影是否符合条件
                if self._is_movie_eligible(movie, min_evaluations, min_score):
                    page_eligible_movies.append(movie)
                    consecutive_failures = 0  # 重置连续失败计数
                else:
                    page_failures += 1
                    consecutive_failures += 1

                    # 如果连续失败超过限制且当前页面上已经有足够多的失败项
                    if consecutive_failures >= consecutive_failures_limit and page_failures >= 3:
                        info(f"连续 {consecutive_failures} 部电影不符合条件，停止获取")
                        current_page = max_page + 1  # 强制结束循环
                        break

            eligible_movies.extend(page_eligible_movies)
            info(f"第 {current_page} 页找到 {len(page_eligible_movies)} 部符合条件的电影")

            current_page += 1
            time.sleep(random.randint(10, 60))  # 减少等待时间，提高效率

        info(f"演员 {actor.name} 共获取到 {len(eligible_movies)} 部符合条件的电影")
        return eligible_movies

    def _build_actor_movies_page_url(self, actor: Actor, page: int) -> str:
        """根据不同来源构建演员电影页面URL"""
        if self.scraper_from == 'javdb':
            actor_uri = actor.javdb_uri
        elif self.scraper_from == 'javbus':
            actor_uri = actor.javbus_uri
        else:
            actor_uri = actor.javlib_uri

        sort_param = f"&sort_type={self.actor_sort_type}" if self.scraper_from == 'javdb' else ""
        return f"{self.base_url}{actor_uri}?page={page}{sort_param}"

    def _is_movie_eligible(self, movie: Dict[str, Any], min_evaluations: int, min_score: float) -> bool:
        """判断电影是否符合条件"""
        # 获取评分和评价人数
        score = float(movie.get('score', 0.0))
        evaluations = int(movie.get('evaluations', 0))

        # 根据条件判断
        if min_evaluations > 0 and evaluations < min_evaluations:
            return False

        if min_score > 0.0 and score < min_score:
            return False

        return True

    def _parse_actor_page_info(self, page_content: str) -> tuple:
        """解析演员页面信息，获取电影数量和最大页数"""
        try:
            return self.parser.parse_actor_page_info(page_content)
        except Exception as e:
            error(f"解析演员页面信息失败: {str(e)}")
            return 0, 0

    def _parse_actor_movies_page(self, page_content: str) -> list:
        """解析演员电影页面，返回符合条件的电影列表"""
        try:
            movies = self.parser.parse_actor_movies_page(page_content,
                                                         min_evaluations=self.actor_min_evaluations)
            return movies if movies else []
        except Exception as e:
            error(f"解析演员电影页面失败: {str(e)}")
            return []

    def _get_actor_details(self, actor_uri: str) -> Dict[str, Any]:
        """获取演员详细信息"""
        if not actor_uri:
            warning("演员URI为空，无法获取详情")
            return {}

        detail_url = f"{self.base_url}{actor_uri}"
        info(f"获取演员详情页: {detail_url}")

        detail_page = self.http_util.request(url=detail_url, cookie=self.cookie)
        if not detail_page:
            warning(f"获取演员详情页失败: {detail_url}")
            return {}

        # 解析演员详情页
        actor_details = self.parser.parse_actor_details_page(detail_page)
        if not actor_details:
            warning(f"解析演员详情页失败: {detail_url}")
            return {}

        info(f"成功获取演员详情: {actor_details.get('name', '未知')}")
        return actor_details