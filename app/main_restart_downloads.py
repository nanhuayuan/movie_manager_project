# main_restart_downloads.py
from sqlalchemy.orm import joinedload
from typing import List, Optional, Dict, Any, Tuple
import time
from dataclasses import dataclass

from app.config.log_config import info, error, debug, LogUtil
from app.main import create_app
from app.model.db.movie_model import Movie
from app.services import JellyfinService, ChartService, MovieService, DownloadService
from app.services.download_failure_service import DownloadFailureService
from app.utils.download_client import DownloadStatus, TorrentInfo
from app.utils.magnet_util import MagnetUtil

logger = LogUtil.get_logger()


class RestartDownloadManager:
    """管理电影下载重试的类，处理下载速度慢或失败的情况"""

    # 定义常量
    MIN_ACCEPTABLE_SPEED = 0  # KB/s，低于此速度视为需要重试
    MAX_RETRY_COUNT = 3  # 最大重试次数
    SPEED_CHECK_PERIOD = 60  # 秒，检查下载速度的时间间隔
    QUALITY_THRESHOLD = 7.0  # 最低可接受质量分数
    ENABLE_SPEED_BASED_SWITCHING = True  # 是否启用速度切换
    ENABLE_SOURCE_SWITCHING = False  # 是否允许切换下载源

    def __init__(self):
        self.chart_service = ChartService()
        self.movie_service = MovieService()
        self.jellyfin_service = JellyfinService()
        self.download_service = DownloadService()
        self.download_failure_service = DownloadFailureService()
        self.magnet_util = MagnetUtil()

        # 添加源质量评估配置
        self.quality_threshold = self.QUALITY_THRESHOLD  # 最低可接受质量分数
        # 可以维护一个源质量评分字典
        self.source_quality_ratings = {}  # 可以从数据库或配置文件加载

        # 统计信息
        self.stats = {
            "total_movies_processed": 0,
            "already_in_library": 0,
            "currently_downloading": 0,
            "download_restarted": 0,
            "new_downloads_added": 0,
            "download_failures": 0,
            "skipped_items": 0
        }

        # 修改缓存结构
        self.all_torrents = {}  # serial_number到种子的映射
        self.all_torrents_by_name = {}  # 原始的以名称为键的字典
        self.cache_updated_time = 0
        self.cache_valid_time = 300 # 缓存有效期，单位秒

    def _update_torrents_cache(self, force=False) -> None:
        """更新种子信息缓存，并建立serial_number到种子的映射"""
        current_time = time.time()
        # 检查缓存是否过期或强制更新
        if force or current_time - self.cache_updated_time > self.cache_valid_time:
            logger.info("更新下载种子缓存信息")
            torrents = self.download_service.get_all_downloads()

            # 保存原始的以名称为键的字典
            self.all_torrents_by_name = {torrent.name: torrent for torrent in torrents}

            # 创建以serial_number为基础的映射
            self.all_torrents = {}
            for torrent in torrents:
                # 从种子名称中提取可能的serial_number
                for serial_number in self._extract_potential_serial_numbers(torrent.name):
                    if serial_number not in self.all_torrents:
                        self.all_torrents[serial_number] = torrent

            self.cache_updated_time = current_time
            logger.info(f"已缓存 {len(torrents)} 个下载任务信息，建立了 {len(self.all_torrents)} 个serial_number映射")

    def _extract_potential_serial_numbers(self, torrent_name: str) -> List[str]:
        """从种子名称中提取可能的serial_number"""
        import re

        # 转换为大写以便统一匹配
        torrent_name = torrent_name.upper()

        patterns = [
            r'([A-Z]+-\d+)',  # 匹配常见AV编号格式如ABC-123
            r'([A-Z]+\d+)',  # 匹配无连字符格式如ABC123
            r'([A-Z]+)(\d+)',  # 捕获字母和数字部分以便重组
            # 更多匹配模式可以根据实际情况添加
        ]

        results = []
        for pattern in patterns:
            matches = re.findall(pattern, torrent_name)

            # 处理元组结果（如模式3）
            for match in matches:
                if isinstance(match, tuple):
                    # 如果是元组，尝试组合不同的格式
                    if len(match) >= 2:
                        # 原始格式
                        results.append(''.join(match))
                        # 带连字符格式
                        results.append(f"{match[0]}-{match[1]}")
                else:
                    results.append(match)

        # 返回去重后的结果
        return list(set(results))

    def _find_torrent_by_serial_number_in_name(self, serial_number: str) -> Optional[TorrentInfo]:
        """通过检查种子名称是否包含序列号来查找种子"""
        # 确保缓存是最新的
        #self._update_torrents_cache()
        start_time = time.time()

        # 先从映射字典中查找（使用之前的提取方法）
        torrent = self.all_torrents.get(serial_number)
        if torrent:
            return torrent

        # 如果没找到，则遍历所有种子检查名称是否包含序列号
        serial_upper = serial_number.upper()  # 转为大写进行比较
        result = None
        for torrent in self.all_torrents_by_name.values():
            if serial_upper in torrent.name.upper():
                logger.debug(f"通过名称包含关系找到种子: {torrent.name} 对应序列号: {serial_number}")
            # 记录性能数据
        elapsed = time.time() - start_time
        if elapsed > 0.1:  # 如果查询时间超过100ms，记录日志
            logger.debug(f"查找种子耗时: {elapsed:.3f}秒, 序列号: {serial_number}")

        return result  # 返回找到的种子

    def get_torrent_for_serial_number(self, serial_number: str, use_extraction=True, use_contains=True) -> Optional[
        TorrentInfo]:
        """获取与序列号关联的种子，可选择使用哪种查找策略

        Args:
            serial_number: 电影序列号
            use_extraction: 是否使用提取番号作为字典key的方式查找
            use_contains: 是否使用遍历检查包含关系的方式查找

        Returns:
            TorrentInfo 或 None（如果未找到）
        """
        # 确保缓存是最新的
        #self._update_torrents_cache()

        # 策略1: 使用提取番号作为字典key的方式
        if use_extraction:
            torrent = self.all_torrents.get(serial_number)
            if torrent:
                logger.debug(f"通过提取番号映射找到种子: {torrent.name}")
                return torrent

        # 策略2: 使用遍历检查包含关系的方式
        if use_contains:
            serial_upper = serial_number.upper()
            for torrent in self.all_torrents_by_name.values():
                if serial_upper in torrent.name.upper():
                    logger.debug(f"通过名称包含关系找到种子: {torrent.name}")
                    return torrent

        return None

    def process_all_charts(self) -> Dict[str, Any]:
        """处理所有榜单中的电影，检查下载状态并在需要时重启下载"""

        logger.info("开始处理所有榜单电影的下载状态")

        # 首先更新种子缓存，一次性获取所有下载信息
        self._update_torrents_cache(force=True)  # 添加强制更新参数

        # 获取本地榜单
        charts = self.chart_service.parse_local_chartlist()
        if not charts:
            logger.warning("未找到任何榜单数据")
            return self.stats

        logger.info(f"找到 {len(charts)} 个榜单")

        for chart in charts:
            self._process_single_chart(chart)

        logger.info("所有榜单处理完成")
        return self.stats

    def _process_single_chart(self, chart) -> None:
        """处理单个榜单中的所有电影条目"""

        logger.info(f"开始处理榜单: {chart.name}")

        chart_entries = list(chart.entries)
        logger.info(f"榜单 '{chart.name}' 共有 {len(chart_entries)} 个条目")

        for entry in chart_entries:
            try:
                self.stats["total_movies_processed"] += 1

                # 跳过特定类型条目
                if entry.serial_number and entry.serial_number.startswith('FC2'):
                    logger.info(f"跳过FC2类型条目: {entry.serial_number}")
                    self.stats["skipped_items"] += 1
                    continue

                logger.debug(f"处理条目: {entry.serial_number}, 榜单: {chart.name}，排行: {entry.rank}/{len(chart_entries)}")

                # 检查是否已在媒体库中
                if self._is_in_media_library(entry.serial_number):
                    self.stats["already_in_library"] += 1
                    continue

                # 获取和处理下载状态
                self._handle_download_status(entry.serial_number)

            except Exception as e:
                logger.error(f"处理榜单条目 '{entry.serial_number}' 时出错: {str(e)}")
                self.stats["download_failures"] += 1

        logger.info(f"榜单 '{chart.name}' 处理完成")

    def _is_in_media_library(self, serial_number: str) -> bool:
        """检查电影是否已经在媒体库中"""

        movie = self.jellyfin_service.get_one_by_serial_number(serial_number=serial_number)
        if movie:
            logger.info(f"电影已在媒体库中: {serial_number}")
            return True
        return False

    def _handle_download_status(self, serial_number: str) -> None:
        """基于当前下载状态处理电影"""
        try:
            # 从缓存中获取种子信息，避免每次单独请求
            #torrent = self.all_torrents.get(serial_number)
            # 可以在这里选择使用哪种查找策略
            # torrent = self.get_torrent_for_serial_number(serial_number, use_extraction=True, use_contains=False)  # 仅使用提取方法
            # torrent = self.get_torrent_for_serial_number(serial_number, use_extraction=False, use_contains=True)  # 仅使用包含关系方法
            torrent = self.get_torrent_for_serial_number(serial_number)  # 使用两种方法（默认）
            if torrent:
                download_status = torrent.status
                logger.debug(f"电影 {serial_number} 已找到对应种子，当前下载状态: {download_status}")
            else:
                download_status = DownloadStatus.CRAWLED
                logger.debug(f"电影 {serial_number} 未找到对应种子，设为默认状态: {download_status}")

            # 根据下载状态处理
            if download_status in [DownloadStatus.COMPLETED.value, DownloadStatus.IN_LIBRARY.value]:
                logger.info(f"电影下载已完成: {serial_number}")
                self.stats["already_in_library"] += 1
                return

            elif DownloadStatus.QUEUED.value <= download_status <= DownloadStatus.COMPLETED.value:
                # 电影正在下载中，检查下载速度
                self.stats["currently_downloading"] += 1

                # 检查是否应该切换源，考虑配置参数和下载速度
                if self.ENABLE_SOURCE_SWITCHING and self._should_switch_source(torrent.hash, torrent.download_speed):
                    self._try_alternative_magnet(serial_number, torrent)
                else:
                    logger.info(f"电影正常下载中或已决定不切换源: {serial_number}")
            else:
                # 电影尚未开始下载或下载状态异常，尝试重新下载
                self._start_new_download(serial_number)
        except Exception as e:
            logger.error(f"处理电影 {serial_number} 下载状态时出错: {str(e)}")
            self.stats["download_failures"] += 1

    def _try_alternative_magnet(self, serial_number: str, current_torrent) -> None:
        """尝试使用替代磁力链接重新下载"""

        logger.info(f"电影 {serial_number} 下载速度过慢，尝试替代链接")

        # 从数据库获取完整电影信息
        movie = self._get_movie_with_full_details(serial_number)
        if not movie:
            logger.warning(f"无法获取电影详细信息: {serial_number}")
            return

        # 获取当前正在下载的磁力链接的哈希值
        current_hash = self.magnet_util.extract_hash(input_string=current_torrent.hash)

        # 获取所有可用的磁力链接并按质量排序
        sorted_magnets = self._sort_magnets_by_quality(movie.magnets)

        # 尝试查找替代磁力链接
        for index, magnet in enumerate(sorted_magnets):
            magnet_link = f"magnet:?xt=urn:btih:{magnet.magnet_xt}"

            # 跳过当前正在使用但速度慢的链接
            if current_hash in magnet_link:
                continue

            # 检查替代磁力链接的可用性
            logger.info(f"尝试替代磁力链接 {index + 1}/{len(sorted_magnets)}: {magnet_link}")
            if self.download_service.check_magnet_availability(magnet=magnet_link):
                # 删除当前慢速任务
                self.download_service.remove_torrent(current_torrent.hash)

                # 添加新的下载任务
                if self.download_service.add_download(magnet_link):
                    logger.info(f"成功切换到替代磁力链接: {serial_number}")
                    self.stats["download_restarted"] += 1
                    # 更新缓存
                    self._update_torrents_cache()
                    return

            logger.debug(f"替代磁力链接不可用: {magnet_link}")

        # 所有磁力链接都尝试失败，记录失败
        logger.warning(f"所有替代磁力链接都不可用: {serial_number}")
        self.download_failure_service.add_download_failed(movie)
        self.stats["download_failures"] += 1

    def _sort_magnets_by_quality(self, magnets) -> List:
        """根据质量评分对磁力链接进行排序，考虑多种因素"""
        rated_magnets = []
        for magnet in magnets:
            hash_value = magnet.magnet_xt

            # 基础质量评分
            base_quality = self.source_quality_ratings.get(hash_value, 5.0)

            # 可以考虑其他因素调整质量评分
            # 例如：文件大小、下载历史、种子数量等
            adjusted_quality = base_quality

            # 如果有历史下载记录，可以调整评分
            if hasattr(magnet, 'size') and magnet.size:
                # 假设大于4GB的内容质量更好
                if magnet.size > 4 * 1024 * 1024 * 1024:
                    adjusted_quality += 1.0

            # 如果有种子数信息，可以进一步调整
            if hasattr(magnet, 'seeds') and magnet.seeds:
                if magnet.seeds > 10:
                    adjusted_quality += 0.5

            rated_magnets.append((magnet, adjusted_quality))

        # 按质量降序排序
        rated_magnets.sort(key=lambda x: x[1], reverse=True)
        return [item[0] for item in rated_magnets]

    def _start_new_download(self, serial_number: str) -> None:
        """开始新的下载任务"""

        logger.info(f"准备为电影添加新的下载任务: {serial_number}")

        # 从数据库获取完整电影信息
        movie = self._get_movie_with_full_details(serial_number)
        if not movie or not movie.magnets:
            logger.warning(f"电影没有可用的磁力链接: {serial_number}")
            self.stats["download_failures"] += 1
            return

        # 获取按质量排序的磁力链接
        sorted_magnets = self._sort_magnets_by_quality(movie.magnets)

        # 尝试所有可用的磁力链接
        for index, magnet in enumerate(sorted_magnets):
            magnet_link = f"magnet:?xt=urn:btih:{magnet.magnet_xt}"

            logger.info(f"尝试磁力链接 {index + 1}/{len(sorted_magnets)}: {magnet_link}")

            # 添加下载任务
            if self.download_service.add_download(magnet_link):
                logger.info(f"下载任务添加成功: {serial_number}")
                self.stats["new_downloads_added"] += 1
                # 更新缓存
                self._update_torrents_cache()
                return

        # 所有磁力链接都下载失败
        logger.warning(f"所有磁力链接都下载失败: {serial_number}")
        self.download_failure_service.add_download_failed(movie)
        self.stats["download_failures"] += 1

    def _get_movie_with_full_details(self, serial_number: str) -> Optional[Movie]:
        """从数据库获取包含所有关联数据的电影信息"""

        return self.movie_service.get_movie_from_db_by_serial_number(
            serial_number=serial_number,
            options=[
                joinedload(Movie.studio),
                joinedload(Movie.actors),
                joinedload(Movie.directors),
                joinedload(Movie.seriess),
                joinedload(Movie.genres),
                joinedload(Movie.labels)
            ]
        )

    def _should_switch_source(self, current_magnet, speed) -> bool:
        """判断是否应该切换源，使用动态速度评估"""
        # 如果功能被禁用，直接返回False
        if not self.ENABLE_SOURCE_SWITCHING or not self.ENABLE_SPEED_BASED_SWITCHING:
            return False

        # 动态速度评估：考虑文件大小、已下载时间等因素
        torrent_hash = self.magnet_util.extract_hash(input_string=current_magnet)

        # 获取对应的种子信息
        torrent_info = None
        for torrent in self.all_torrents_by_name.values():
            if torrent.hash == torrent_hash:
                torrent_info = torrent
                break

        if not torrent_info:
            return False

        # 计算已下载时间（秒）
        download_time = torrent_info.time_active

        # 如果下载时间超过一定阈值（如30分钟）且速度仍然很低
        if download_time > 1800 and speed <= self.MIN_ACCEPTABLE_SPEED:
            # 考虑当前源质量
            source_hash = torrent_hash
            current_quality = self.source_quality_ratings.get(source_hash, 5.0)

            # 质量评估逻辑
            if current_quality < self.quality_threshold:
                logger.info(f"下载速度持续较慢 ({speed} KB/s)，已下载{download_time / 60:.1f}分钟，源质量评分 ({current_quality})，决定切换源")
                return True

        return False


def process_restart_downloads():
    start_time = time.time()
    manager = RestartDownloadManager()
    stats = manager.process_all_charts()

    # 输出统计信息
    execution_time = time.time() - start_time
    info(f"电影下载状态处理任务完成, 耗时: {execution_time:.2f}秒")
    info("=== 统计信息 ===")
    info(f"总处理电影数: {stats['total_movies_processed']}")
    info(f"已在媒体库中: {stats['already_in_library']}")
    info(f"正在下载中: {stats['currently_downloading']}")
    info(f"重新启动下载: {stats['download_restarted']}")
    info(f"新增下载任务: {stats['new_downloads_added']}")
    info(f"下载失败数: {stats['download_failures']}")
    info(f"跳过条目数: {stats['skipped_items']}")
def main():
    """应用入口函数"""
    try:
        app = create_app()
        with app.app_context():
            process_restart_downloads()

    except Exception as e:
        error(f"处理电影下载状态时发生错误: {str(e)}")
        raise


if __name__ == '__main__':
    main()