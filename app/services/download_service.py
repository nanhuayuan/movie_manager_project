from app.utils.download_client import TorrentInfo, DownloadClientEnum, DownloadStatus, TaskPriority
from app.utils.download_client import QBittorrentClient, BitCometClient, TransmissionClient
from app.config.app_config import AppConfig
from typing import Optional, List, Callable, Dict, Any, TypeVar, Union
from datetime import datetime, timedelta
import threading
import time
import functools
from app.config.log_config import info, error
from dataclasses import dataclass
from app.utils.magnet_util import MagnetUtil
from app.utils.retry_utils import retry

@dataclass
class ScheduledTask:
    """计划任务"""
    task_id: str
    torrent_hash: str
    action: str  # 'start', 'pause', 'remove'
    schedule_time: datetime
    repeat: bool
    interval: int  # seconds
    last_run: Optional[datetime]
    enabled: bool


class DownloadService:
    """下载服务类，处理下载任务的管理和监控"""

    def __init__(self):
        """初始化下载服务"""
        self.config = AppConfig().get_download_client_config()
        self.host = self.config.get('host', '127.0.0.1')
        self.port = self.config.get('port', 6363)
        self.username = self.config.get('username', 'admin')
        self.password = self.config.get('password', 'adminadmin')
        self.client_type = self.config.get('type', DownloadClientEnum.QBITTORRENT.value)
        self.speed_limit = self.config.get('type', 7 * 1024 * 1024)  # 默认 7MB/s
        self.max_retries = self.config.get('add_torrent_max_retries', 3)
        self.client = self.create_client()
        self.client.connect()
        self.magnet_util = MagnetUtil()

        # 计划任务相关
        self._scheduled_tasks: Dict[str, ScheduledTask] = {}
        self._scheduler_thread = None
        self._scheduler_running = False
        self._start_scheduler()

        # 重试计数和速度历史
        self._retry_counts = {}
        self._speed_history = {}

    ## 以下未改动
    # 计划任务相关方法
    def _start_scheduler(self):
        """启动计划任务调度器"""
        self._scheduler_running = True
        self._scheduler_thread = threading.Thread(target=self._scheduler_loop)
        self._scheduler_thread.daemon = True
        self._scheduler_thread.start()
    def _scheduler_loop(self):
        """计划任务调度循环"""
        while self._scheduler_running:
            now = datetime.now()
            for task_id, task in list(self._scheduled_tasks.items()):
                if not task.enabled:
                    continue

                if task.last_run is None or \
                        (task.repeat and (now - task.last_run).total_seconds() >= task.interval):
                    if now >= task.schedule_time:
                        self._execute_scheduled_task(task)
                        task.last_run = now
                        if not task.repeat:
                            task.enabled = False

            time.sleep(1)

    def _execute_scheduled_task(self, task: ScheduledTask):
        """执行计划任务"""
        try:
            if task.action == 'start':
                self.resume_download(task.torrent_hash)
            elif task.action == 'pause':
                self.pause_download(task.torrent_hash)
            elif task.action == 'remove':
                self.remove_download(task.torrent_hash)
        except Exception as e:
            print(f"执行计划任务出错: {e}")

    def add_scheduled_task(self, torrent_hash: str, action: str,
                           schedule_time: datetime,
                           repeat: bool = False,
                           interval: int = 0) -> str:
        """添加计划任务

        Args:
            torrent_hash: 种子哈希
            action: 动作('start', 'pause', 'remove')
            schedule_time: 计划执行时间
            repeat: 是否重复执行
            interval: 重复间隔(秒)
        Returns:
            str: 任务ID
        """
        task_id = f"{torrent_hash}_{action}_{int(time.time())}"
        task = ScheduledTask(
            task_id=task_id,
            torrent_hash=torrent_hash,
            action=action,
            schedule_time=schedule_time,
            repeat=repeat,
            interval=interval,
            last_run=None,
            enabled=True
        )
        self._scheduled_tasks[task_id] = task
        return task_id

    def remove_scheduled_task(self, task_id: str) -> bool:
        """删除计划任务"""
        if task_id in self._scheduled_tasks:
            del self._scheduled_tasks[task_id]
            return True
        return False

    def get_scheduled_tasks(self) -> List[ScheduledTask]:
        """获取所有计划任务"""
        return list(self._scheduled_tasks.values())

    def batch_add_downloads(self, magnets: List[str],
                            save_path: Optional[str] = None) -> Dict[str, bool]:
        """批量添加下载任务
        Returns:
            Dict[str, bool]: 每个磁力链接的添加结果
        """
        results = {}
        for magnet in magnets:
            try:
                success = self.add_download(magnet, save_path)
                results[magnet] = success
            except Exception as e:
                print(f"添加下载任务出错: {e}")
                results[magnet] = False
        return results

    def batch_pause_downloads(self, torrent_hashes: List[str]) -> Dict[str, bool]:
        """批量暂停下载任务"""
        results = {}
        for torrent_hash in torrent_hashes:
            try:
                success = self.pause_download(torrent_hash)
                results[torrent_hash] = success
            except Exception as e:
                print(f"暂停下载任务出错: {e}")
                results[torrent_hash] = False
        return results

    def batch_resume_downloads(self, torrent_hashes: List[str]) -> Dict[str, bool]:
        """批量恢复下载任务"""
        results = {}
        for torrent_hash in torrent_hashes:
            try:
                success = self.resume_download(torrent_hash)
                results[torrent_hash] = success
            except Exception as e:
                print(f"恢复下载任务出错: {e}")
                results[torrent_hash] = False
        return results

    def batch_remove_downloads(self, torrent_hashes: List[str],
                               delete_files: bool = False) -> Dict[str, bool]:
        """批量删除下载任务"""
        results = {}
        for torrent_hash in torrent_hashes:
            try:
                success = self.remove_download(torrent_hash, delete_files)
                results[torrent_hash] = success
            except Exception as e:
                print(f"删除下载任务出错: {e}")
                results[torrent_hash] = False
        return results

    def get_client_status(self) -> dict:
        """获取客户端状态信息"""
        stats = self.get_download_stats()
        return {
            'client_type': self.client_type,
            'connection_status': 'connected' if self.client else 'disconnected',
            'download_limit': self.speed_limit,
            'current_stats': stats,
            'disk_cache': self._get_disk_cache_info(),
            'network_status': self._get_network_status()
        }

    def _get_disk_cache_info(self) -> dict:
        """获取磁盘缓存信息"""
        # 这个方法需要根据具体的下载客户端API来实现
        try:
            if self.client_type == DownloadClientEnum.QBITTORRENT.value:
                app_info = self.client.app.preferences
                return {
                    'disk_cache': app_info.disk_cache,
                    'disk_cache_ttl': app_info.disk_cache_ttl
                }
            return {}
        except:
            return {}

    def _get_network_status(self) -> dict:
        """获取网络状态信息"""
        try:
            total_speed = self.get_total_speed()
            active_downloads = self.get_active_downloads()
            return {
                'total_download_speed': total_speed,
                'active_connections': sum(t.num_peers for t in active_downloads),
                'total_seeds': sum(t.num_seeds for t in active_downloads)
            }
        except:
            return {}

    def retry_failed_downloads(self, max_retries: int = 3) -> Dict[str, bool]:
        """重试失败的下载任务
            Dict[str, bool]: 重试结果
        """
        failed_downloads = self.get_error_downloads()
        results = {}

        for torrent in failed_downloads:
            try:
                # 检查重试次数
                retry_count = self._get_retry_count(torrent.hash)
                if retry_count >= max_retries:
                    results[torrent.hash] = False
                    continue

                # 暂停任务
                self.pause_download(torrent.hash)
                time.sleep(1)

                # 重新开始任务
                success = self.resume_download(torrent.hash)
                self._increment_retry_count(torrent.hash)

                results[torrent.hash] = success
            except Exception as e:
                print(f"重试下载任务出错: {e}")
                results[torrent.hash] = False

        return results

    def _get_retry_count(self, torrent_hash: str) -> int:
        """获取重试次数"""
        if not hasattr(self, '_retry_counts'):
            self._retry_counts = {}
        return self._retry_counts.get(torrent_hash, 0)

    def _increment_retry_count(self, torrent_hash: str):
        """增加重试次数"""
        if not hasattr(self, '_retry_counts'):
            self._retry_counts = {}
        self._retry_counts[torrent_hash] = self._get_retry_count(torrent_hash) + 1


    def get_download_speed_history(self, torrent_hash: str,
                                   duration: int = 3600) -> List[tuple]:
        """获取下载速度历史
        Returns:
            List[tuple]: (timestamp, speed)列表
        """
        if not hasattr(self, '_speed_history'):
            self._speed_history = {}

        if torrent_hash not in self._speed_history:
            self._speed_history[torrent_hash] = []

        # 清理过期数据
        current_time = time.time()
        self._speed_history[torrent_hash] = [
            (t, s) for t, s in self._speed_history[torrent_hash]
            if current_time - t <= duration
        ]

        return self._speed_history[torrent_hash]

    def update_speed_history(self):
        """更新所有任务的速度历史"""
        if not hasattr(self, '_speed_history'):
            self._speed_history = {}

        current_time = time.time()
        for torrent in self.get_active_downloads():
            if torrent.hash not in self._speed_history:
                self._speed_history[torrent.hash] = []
            self._speed_history[torrent.hash].append(
                (current_time, torrent.download_speed)
            )

    def export_task_report(self, start_time: datetime = None,
                           end_time: datetime = None) -> dict:
        """导出下载任务报告
            dict: 报告数据
        """
        if end_time is None:
            end_time = datetime.now()
        if start_time is None:
            start_time = end_time - timedelta(days=7)

        history = self.client.get_download_history()
        filtered_history = [
            h for h in history
            if start_time <= h.start_time <= end_time
        ]

        total_downloaded = sum(h.downloaded_bytes for h in filtered_history)
        success_count = len([h for h in filtered_history
                             if h.final_status == DownloadStatus.COMPLETED])

        return {
            'period': {
                'start': start_time,
                'end': end_time
            },
            'summary': {
                'total_tasks': len(filtered_history),
                'success_count': success_count,
                'fail_count': len(filtered_history) - success_count,
                'total_downloaded': total_downloaded,
                'success_rate': success_count / len(filtered_history) if filtered_history else 0
            },
            'details': [
                {
                    'name': h.name,
                    'start_time': h.start_time,
                    'end_time': h.end_time,
                    'status': h.final_status,
                    'downloaded': h.downloaded_bytes,
                    'average_speed': h.average_speed,
                    'error': h.error_message
                }
                for h in filtered_history
            ]
        }

    def optimize_active_tasks(self):
        """优化活动任务的性能

        - 暂停低优先级的任务以让出带宽
        - 调整任务优先级
        - 限制同时活动的任务数
        """
        active_tasks = self.get_active_downloads()
        if not active_tasks:
            return

        # 按优先级排序
        tasks_by_priority = sorted(
            active_tasks,
            key=lambda t: self.client.get_task_priority(t.hash).value,
            reverse=True
        )

        # 限制同时活动的任务数
        max_active = 3  # 可以根据配置调整
        if len(tasks_by_priority) > max_active:
            for task in tasks_by_priority[max_active:]:
                self.pause_download(task.hash)

        # 调整任务的速度限制
        available_bandwidth = self.speed_limit
        for task in tasks_by_priority[:max_active]:
            # 根据优先级分配带宽
            priority = self.client.get_task_priority(task.hash)
            if priority == TaskPriority.URGENT:
                task_limit = available_bandwidth * 0.5
            elif priority == TaskPriority.HIGH:
                task_limit = available_bandwidth * 0.3
            else:
                task_limit = available_bandwidth * 0.2

            self.client.set_download_limit(task_limit)

    def cleanup(self):
        """清理资源并关闭服务"""
        # 停止调度器
        if self._scheduler_running:
            self._scheduler_running = False
            if self._scheduler_thread:
                self._scheduler_thread.join()

        # 保存历史记录
        if hasattr(self, '_speed_history'):
            # 可以将历史记录保存到文件或数据库
            pass

        # 断开客户端连接
        if self.client:
            self.client.disconnect()

    # 已上未改动
    # 以下已根据你提供的更新 还是
    def create_client(self, host: str = None, port: int = None, username: str = None,
                      password: str = None, client_type: str = None):
        """创建下载客户端实例"""
        client_map = {
            DownloadClientEnum.QBITTORRENT.value: QBittorrentClient,
            DownloadClientEnum.BITCOMET.value: BitCometClient,
            DownloadClientEnum.TRANSMISSION.value: TransmissionClient
        }

        client_type = client_type or self.client_type
        client_class = client_map.get(client_type)
        if not client_class:
            raise ValueError(f"不支持的下载客户端类型: {client_type}")

        return client_class(
            host=host or self.host,
            port=port or self.port,
            username=username or self.username,
            password=password or self.password
        )

    # 使用重试装饰器
    @retry(max_retries=3, exceptions=(Exception,))
    def add_download(self, magnet: str, save_path: Optional[str] = None) -> bool:
        """添加下载任务"""
        return self.client.add_torrent(magnet, save_path)

    @retry(max_retries=2, exceptions=(Exception,))
    def remove_download(self, torrent_hash: str, delete_files: bool = False) -> bool:
        """删除下载任务"""
        return self.client.remove_torrent(torrent_hash, delete_files)

    @retry(max_retries=2, exceptions=(Exception,))
    def pause_download(self, torrent_hash: str) -> bool:
        """暂停下载任务"""
        return self.client.pause_torrent(torrent_hash)

    @retry(max_retries=2, exceptions=(Exception,))
    def resume_download(self, torrent_hash: str) -> bool:
        """恢复下载任务"""
        return self.client.resume_torrent(torrent_hash)

    @retry(max_retries=2, exceptions=(Exception,))
    def get_download_info(self, torrent_hash: str) -> Optional[TorrentInfo]:
        """获取下载任务信息"""
        return self.client.get_torrent_info(torrent_hash)

    @retry(max_retries=2, exceptions=(Exception,))
    def get_all_downloads(self) -> List[TorrentInfo]:
        """获取所有下载任务信息"""
        return self.client.get_all_torrents()

    # 批量操作方法
    def batch_operation(self, operation_func, items, **kwargs) -> Dict[str, bool]:
        """通用批量操作方法"""
        results = {}
        for item in items:
            try:
                success = operation_func(item, **kwargs)
                results[item] = success
            except Exception as e:
                error(f"{operation_func.__name__} 执行出错: {e}")
                results[item] = False
        return results

    def batch_add_downloads(self, magnets: List[str], save_path: Optional[str] = None) -> Dict[str, bool]:
        """批量添加下载任务"""
        return self.batch_operation(self.add_download, magnets, save_path=save_path)

    def batch_pause_downloads(self, torrent_hashes: List[str]) -> Dict[str, bool]:
        """批量暂停下载任务"""
        return self.batch_operation(self.pause_download, torrent_hashes)

    def batch_resume_downloads(self, torrent_hashes: List[str]) -> Dict[str, bool]:
        """批量恢复下载任务"""
        return self.batch_operation(self.resume_download, torrent_hashes)

    def batch_remove_downloads(self, torrent_hashes: List[str], delete_files: bool = False) -> Dict[str, bool]:
        """批量删除下载任务"""
        return self.batch_operation(self.remove_download, torrent_hashes, delete_files=delete_files)

    # 下载状态查询方法
    def get_downloads_by_status(self, status: DownloadStatus) -> List[TorrentInfo]:
        """获取指定状态的下载任务"""
        return [t for t in self.get_all_downloads() if t.status == status]

    def get_completed_downloads(self) -> List[TorrentInfo]:
        """获取已完成的下载任务"""
        return self.get_downloads_by_status(DownloadStatus.COMPLETED)

    def get_active_downloads(self) -> List[TorrentInfo]:
        """获取正在下载的任务"""
        return self.get_downloads_by_status(DownloadStatus.DOWNLOADING)

    def get_queued_downloads(self) -> List[TorrentInfo]:
        """获取排队中的下载任务"""
        return self.get_downloads_by_status(DownloadStatus.QUEUED)

    def get_paused_downloads(self) -> List[TorrentInfo]:
        """获取已暂停的下载任务"""
        return self.get_downloads_by_status(DownloadStatus.PAUSED)

    def get_error_downloads(self) -> List[TorrentInfo]:
        """获取出错的下载任务"""
        return self.get_downloads_by_status(DownloadStatus.ERROR)

    # 种子查询方法
    def get_torrent_by_name(self, name: str) -> Optional[TorrentInfo]:
        """根据电影名称搜索下载任务"""
        for torrent in self.get_all_downloads():
            if name.lower() in torrent.name.lower():
                return torrent
        return None

    @retry(max_retries=2, exceptions=(Exception,))
    def get_torrent_by_hash(self, hash_str: str) -> Optional[TorrentInfo]:
        """根据哈希值搜索下载任务"""
        hash_new = self.magnet_util.extract_hash(input_string=hash_str)
        return self.client.get_torrent_info_by_hash(hash_new)

    # 状态和速度查询方法
    def get_total_speed(self) -> int:
        """获取总下载速度"""
        return sum(t.download_speed for t in self.get_all_downloads())

    def get_torrent_speed(self, torrent_hash: str) -> int:
        """获取指定种子的下载速度"""
        torrent = self.get_download_info(torrent_hash)
        return torrent.download_speed if torrent else 0

    def is_speed_limit_exceeded(self) -> bool:
        """检查是否超过速度限制"""
        return self.get_total_speed() > self.speed_limit

    def get_download_status(self, name: str = None, hash_str: str = None) -> int:
        """获取指定内容的下载状态"""
        if name is None and hash_str is None:
            raise ValueError("必须提供name或hash参数之一")

        try:
            torrent = self.get_torrent_by_hash(hash_str) if hash_str else self.get_torrent_by_name(name)
            return torrent.status if torrent else DownloadStatus.DOWNLOAD_FAILED
        except Exception as e:
            error(f"查询种子下载状态失败: {str(e)}")
            return DownloadStatus.DOWNLOAD_FAILED

    def get_download_stats(self) -> dict:
        """获取下载统计信息"""
        downloads = self.get_all_downloads()

        # 使用列表推导式计算各状态数量
        status_counts = {
            status: len([t for t in downloads if t.status == status])
            for status in [DownloadStatus.DOWNLOADING, DownloadStatus.COMPLETED,
                           DownloadStatus.PAUSED, DownloadStatus.ERROR]
        }

        return {
            'total_count': len(downloads),
            'downloading_count': status_counts.get(DownloadStatus.DOWNLOADING, 0),
            'completed_count': status_counts.get(DownloadStatus.COMPLETED, 0),
            'paused_count': status_counts.get(DownloadStatus.PAUSED, 0),
            'error_count': status_counts.get(DownloadStatus.ERROR, 0),
            'total_speed': self.get_total_speed(),
            'total_size': sum(t.size for t in downloads),
            'total_downloaded': sum(t.downloaded for t in downloads)
        }

    # 磁力链接可用性检查
    @retry(max_retries=2, exceptions=(Exception,))
    def check_magnet_availability(self, magnet: str) -> bool:
        """检查磁力链接是否可用"""
        try:
            # 尝试添加种子但不开始下载
            result = self.client.add_torrent(magnet)
            if result:
                # 等待几秒检查是否有连接的peers
                time.sleep(5)
                torrent_hash = magnet.split('btih:')[1][:40]
                torrent = self.get_download_info(torrent_hash)
                if torrent and (torrent.num_seeds > 0 or torrent.num_peers > 0):
                    # 可用时删除测试添加的种子
                    self.remove_download(torrent.hash)
                    return True
            return False
        except Exception:
            return False

    # 计划任务相关方法
    def _start_scheduler(self):
        """启动计划任务调度器"""
        self._scheduler_running = True
        self._scheduler_thread = threading.Thread(target=self._scheduler_loop)
        self._scheduler_thread.daemon = True
        self._scheduler_thread.start()

    def _scheduler_loop(self):
        """计划任务调度循环"""
        while self._scheduler_running:
            now = datetime.now()
            for task_id, task in list(self._scheduled_tasks.items()):
                if not task.enabled:
                    continue

                if task.last_run is None or \
                        (task
    # 已上已根据你提供的更新 结束，明显未完成