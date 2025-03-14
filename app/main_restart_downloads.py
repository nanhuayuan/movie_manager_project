# main_restart_downloads.py
from sqlalchemy.orm import joinedload
from typing import List, Optional, Dict, Any
import time

from app.config.log_config import info, error, debug, LogUtil
from app.main import create_app
from app.model.db.movie_model import Movie
from app.services import JellyfinService, ChartService, MovieService, DownloadService
from app.services.download_failure_service import DownloadFailureService
from app.utils.download_client import DownloadStatus
from app.utils.magnet_util import MagnetUtil

logger = LogUtil.get_logger()


class RestartDownloadManager:
    """管理电影下载重试的类，处理下载速度慢或失败的情况"""

    # 定义常量
    MIN_ACCEPTABLE_SPEED = 100  # KB/s，低于此速度视为需要重试
    MAX_RETRY_COUNT = 3  # 最大重试次数
    SPEED_CHECK_PERIOD = 60  # 秒，检查下载速度的时间间隔
    QUALITY_THRESHOLD = 7.0 # # 最低可接受质量分数
    ENABLE_SPEED_BASED_SWITCHING = True # 是否启用速度切换

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

    def process_all_charts(self) -> Dict[str, Any]:
        """处理所有榜单中的电影，检查下载状态并在需要时重启下载"""

        logger.info("开始处理所有榜单电影的下载状态")

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

        # 获取当前下载状态
        torrent = self.download_service.get_torrent_by_name(name=serial_number)
        download_status = torrent.status if torrent else DownloadStatus.CRAWLED
        logger.debug(f"电影 {serial_number} 当前下载状态: {download_status}")

        # 根据下载状态处理
        if download_status in [DownloadStatus.COMPLETED.value, DownloadStatus.IN_LIBRARY.value]:
            logger.info(f"电影下载已完成: {serial_number}")
            self.stats["already_in_library"] += 1
            return

        elif DownloadStatus.QUEUED.value <= download_status <= DownloadStatus.COMPLETED.value:
            # 电影正在下载中，检查下载速度
            self.stats["currently_downloading"] += 1
            #if self._should_switch_source(torrent.hash, torrent.download_speed):
            if torrent.download_speed <= self.MIN_ACCEPTABLE_SPEED:
                self._try_alternative_magnet(serial_number, torrent)
            else:
                logger.info(f"电影正常下载中或决定不切换源，速度正常: {serial_number}")
        else:
            # 电影尚未开始下载或下载状态异常，尝试重新下载
            self._start_new_download(serial_number)

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

        # 尝试查找替代磁力链接
        for index, magnet in enumerate(movie.magnets):
            magnet_link = f"magnet:?xt=urn:btih:{magnet.magnet_xt}"

            # 跳过当前正在使用但速度慢的链接
            if current_hash in magnet_link:
                continue

            # 检查替代磁力链接的可用性
            logger.info(f"尝试替代磁力链接 {index + 1}/{len(movie.magnets)}: {magnet_link}")
            if self.download_service.check_magnet_availability(magnet=magnet_link):
                # 删除当前慢速任务
                self.download_service.remove_torrent(current_torrent.hash)

                # 添加新的下载任务
                if self.download_service.add_download(magnet_link):
                    logger.info(f"成功切换到替代磁力链接: {serial_number}")
                    self.stats["download_restarted"] += 1
                    return

            logger.debug(f"替代磁力链接不可用: {magnet_link}")

        # 所有磁力链接都尝试失败，记录失败
        logger.warning(f"所有替代磁力链接都不可用: {serial_number}")
        self.download_failure_service.add_download_failed(movie)
        self.stats["download_failures"] += 1

    def _start_new_download(self, serial_number: str) -> None:
        """开始新的下载任务"""

        logger.info(f"准备为电影添加新的下载任务: {serial_number}")

        # 从数据库获取完整电影信息
        movie = self._get_movie_with_full_details(serial_number)
        if not movie or not movie.magnets:
            logger.warning(f"电影没有可用的磁力链接: {serial_number}")
            self.stats["download_failures"] += 1
            return

        # 尝试所有可用的磁力链接
        for index, magnet in enumerate(movie.magnets):
            magnet_link = f"magnet:?xt=urn:btih:{magnet.magnet_xt}"

            logger.info(f"尝试磁力链接 {index + 1}/{len(movie.magnets)}: {magnet_link}")

            # 添加下载任务
            if self.download_service.add_download(magnet_link):
                logger.info(f"下载任务添加成功: {serial_number}")
                self.stats["new_downloads_added"] += 1
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

    def _should_switch_source(self, current_magnet, speed):
        """判断是否应该切换源，考虑速度和质量因素"""
        # 如果速度检查被禁用，直接返回False
        if not self.ENABLE_SPEED_BASED_SWITCHING:
            return False

        # 如果速度太慢
        if speed <= self.MIN_ACCEPTABLE_SPEED:
            # 获取当前源的质量评分
            source_hash = self.magnet_util.extract_hash(input_string=current_magnet)
            current_quality = self.source_quality_ratings.get(source_hash, 5.0)  # 默认中等质量

            # 如果当前源质量高于阈值，即使速度慢也不切换
            if current_quality >= self.quality_threshold:
                logger.info(f"虽然下载速度慢，但源质量较高 ({current_quality})，不切换源")
                return False

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