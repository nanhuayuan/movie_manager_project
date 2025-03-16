from app.utils.download_client import TorrentInfo, DownloadClientEnum, DownloadStatus, TaskPriority
from app.utils.download_client import QBittorrentClient, BitCometClient, TransmissionClient
from app.config.app_config import AppConfig
from typing import Optional, List, Dict
from datetime import datetime, timedelta
import threading
import time
from app.config.log_config import info, error
from dataclasses import dataclass
from app.utils.magnet_util import MagnetUtil
from app.utils.retry_utils import retry, retry_on_connection_error


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
    def __init__(self):
        self.config = AppConfig().get_download_client_config()
        self.host = self.config.get('host', '127.0.0.1')
        self.port = self.config.get('port', 6363)
        self.username = self.config.get('username', 'admin')
        self.password = self.config.get('password', 'adminadmin')
        self.client_type = self.config.get('type', DownloadClientEnum.QBITTORRENT.value)
        self.speed_limit = self.config.get('speed_limit', 7 * 1024 * 1024)  # 默认 7MB/s
        self.max_retries = self.config.get('add_torrent_max_retries', 3)

        # 初始化需要的属性
        self._speed_history = {}
        self._retry_counts = {}
        self._scheduled_tasks = {}
        self._scheduler_thread = None
        self._scheduler_running = False

        # 添加线程锁
        self._speed_history_lock = threading.Lock()
        self._scheduled_tasks_lock = threading.Lock()

        # 创建客户端并连接
        self.client = self.create_client()
        self._connect_with_retry()
        self.magnet_util = MagnetUtil()

        # 启动调度器
        self._start_scheduler()

    @retry_on_connection_error(max_retries=3, delay=1.0, backoff=2.0)
    def _connect_with_retry(self):
        """使用重试机制连接下载客户端"""
        self.client.connect()

    @retry_on_connection_error(max_retries=3, delay=1.0, backoff=2.0)
    def connect_client(self):
        """使用重试装饰器连接下载客户端"""
        self.client.connect()
        info("成功连接到下载客户端")
    def _start_scheduler(self):
        self._scheduler_running = True
        self._scheduler_thread = threading.Thread(target=self._scheduler_loop)
        self._scheduler_thread.daemon = True
        self._scheduler_thread.start()

    def _scheduler_loop(self):
        while self._scheduler_running:
            now = datetime.now()

            # 复制任务列表以避免在迭代中修改
            with self._scheduled_tasks_lock:
                current_tasks = list(self._scheduled_tasks.items())

            for task_id, task in current_tasks:
                if not task.enabled:
                    continue

                if task.last_run is None or \
                        (task.repeat and (now - task.last_run).total_seconds() >= task.interval):
                    if now >= task.schedule_time:
                        self._execute_scheduled_task(task)

                        with self._scheduled_tasks_lock:
                            if task_id in self._scheduled_tasks:  # 再次检查任务是否仍存在
                                self._scheduled_tasks[task_id].last_run = now
                                if not task.repeat:
                                    self._scheduled_tasks[task_id].enabled = False

            time.sleep(1)

    @retry(max_retries=3, exceptions=(Exception,), delay=1.0, backoff=2.0)
    def _execute_scheduled_task(self, task: ScheduledTask):
        """执行计划任务，使用重试装饰器"""
        if task.action == 'start':
            self.resume_download(task.torrent_hash)
        elif task.action == 'pause':
            self.pause_download(task.torrent_hash)
        elif task.action == 'remove':
            self.remove_download(task.torrent_hash)

    def add_scheduled_task(self, torrent_hash: str, action: str,
                           schedule_time: datetime,
                           repeat: bool = False,
                           interval: int = 0) -> str:
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

        with self._scheduled_tasks_lock:
            self._scheduled_tasks[task_id] = task

        return task_id

    def remove_scheduled_task(self, task_id: str) -> bool:
        if task_id in self._scheduled_tasks:
            del self._scheduled_tasks[task_id]
            return True
        return False

    def get_scheduled_tasks(self) -> List[ScheduledTask]:
        return list(self._scheduled_tasks.values())

    @retry_on_connection_error(max_retries=3)
    def export_task_report(self, start_time: datetime = None,
                           end_time: datetime = None) -> dict:
        """导出任务报告，使用重试机制"""
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

        # 防止除零错误
        success_rate = 0
        if filtered_history:
            success_rate = success_count / len(filtered_history)

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
                'success_rate': success_rate
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

    @retry_on_connection_error(max_retries=3)
    def optimize_active_tasks(self):
        """优化活跃任务的带宽分配"""
        active_tasks = self.get_active_downloads()
        if not active_tasks:
            return

        # 按优先级排序
        tasks_by_priority = sorted(
            active_tasks,
            key=lambda t: self.client.get_task_priority(t.hash).value,
            reverse=True
        )

        # 配置可以从配置文件中获取
        max_active = self.config.get('max_active_tasks', 3)

        # 暂停低优先级任务
        if len(tasks_by_priority) > max_active:
            for task in tasks_by_priority[max_active:]:
                self.pause_download(task.hash)
                info(f"由于任务过多，暂停低优先级任务: {task.name}")

        # 计算每个任务的带宽限制
        available_bandwidth = self.speed_limit
        active_count = min(len(tasks_by_priority), max_active)

        if active_count == 0:
            return

        # 按优先级分配带宽
        priorities = [self.client.get_task_priority(t.hash) for t in tasks_by_priority[:active_count]]
        priority_weights = []

        for priority in priorities:
            if priority == TaskPriority.URGENT:
                priority_weights.append(3)
            elif priority == TaskPriority.HIGH:
                priority_weights.append(2)
            else:
                priority_weights.append(1)

        total_weight = sum(priority_weights)
        if total_weight == 0:
            # 平均分配
            per_task_limit = available_bandwidth / active_count
            for task in tasks_by_priority[:active_count]:
                self.client.set_download_limit_for_torrent(task.hash, per_task_limit)
        else:
            # 按权重分配
            for i, task in enumerate(tasks_by_priority[:active_count]):
                task_limit = available_bandwidth * (priority_weights[i] / total_weight)
                self.client.set_download_limit_for_torrent(task.hash, task_limit)
                info(f"为任务 {task.name} 设置带宽限制: {task_limit / 1024 / 1024:.2f} MB/s")

    def cleanup(self):
        """释放资源并断开连接"""
        # 停止调度器
        if hasattr(self, '_scheduler_running') and self._scheduler_running:
            self._scheduler_running = False
            if hasattr(self, '_scheduler_thread') and self._scheduler_thread:
                self._scheduler_thread.join(timeout=2.0)  # 最多等待2秒

        # 保存历史记录
        if hasattr(self, '_speed_history') and self._speed_history:
            # 可以将历史记录保存到文件或数据库
            info("保存下载速度历史记录")
            try:
                # 这里可以添加保存逻辑
                pass
            except Exception as e:
                error(f"保存速度历史记录失败: {str(e)}")

        # 断开客户端连接
        if hasattr(self, 'client') and self.client:
            try:
                self.client.disconnect()
                info("已断开与下载客户端的连接")
            except Exception as e:
                error(f"断开下载客户端连接失败: {str(e)}")

    @retry_on_connection_error(max_retries=3)
    def create_client(self, host: str = None, port: int = None, username: str = None,
                      password: str = None, client_type: str = None):
        """创建下载客户端，使用重试机制"""
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

    @retry_on_connection_error(max_retries=3, delay=1.0, backoff=2.0)
    def create_client_2(self, host: str = None, port: int = None, username: str = None,
                      password: str = None, client_type: str = None):
        """创建下载客户端，使用重试机制"""
        client_type = client_type or self.client_type

        if client_type == DownloadClientEnum.QBITTORRENT.value:
            client = QBittorrentClient(host or self.host, port or self.port,
                                       username or self.username, password or self.password)
        elif client_type == DownloadClientEnum.BITCOMET.value:
            client = BitCometClient(host or self.host, port or self.port,
                                    username or self.username, password or self.password)
        elif client_type == DownloadClientEnum.TRANSMISSION.value:
            client = TransmissionClient(host or self.host, port or self.port,
                                        username or self.username, password or self.password)
        else:
            raise ValueError(f"不支持的下载客户端类型: {client_type}")

        return client

    @retry_on_connection_error(max_retries=3)
    def batch_add_downloads(self, magnets: List[str], save_path: Optional[str] = None) -> Dict[str, bool]:
        results = {}
        for magnet in magnets:
            try:
                success = self.add_download(magnet, save_path)
                results[magnet] = success
            except Exception as e:
                error(f"添加下载任务出错: {e}")
                results[magnet] = False
        return results

    @retry_on_connection_error(max_retries=3)
    def batch_add_downloads_concurrent(self, magnets: List[str], save_path: Optional[str] = None) -> Dict[str, bool]:
        """并发批量添加下载任务"""
        from concurrent.futures import ThreadPoolExecutor
        results = {}

        def add_single_download(magnet):
            try:
                success = self.add_download(magnet, save_path)
                return magnet, success
            except Exception as e:
                error(f"添加下载任务失败: {magnet}, 错误: {e}")
                return magnet, False

        # 使用线程池并发处理
        with ThreadPoolExecutor(max_workers=min(10, len(magnets))) as executor:
            futures = [executor.submit(add_single_download, magnet) for magnet in magnets]

            for future in futures:
                try:
                    magnet, success = future.result()
                    results[magnet] = success
                except Exception as e:
                    error(f"处理添加下载任务结果失败: {e}")

        return results

    @retry_on_connection_error(max_retries=3)
    def batch_pause_downloads(self, torrent_hashes: List[str]) -> Dict[str, bool]:
        results = {}
        for torrent_hash in torrent_hashes:
            try:
                success = self.pause_download(torrent_hash)
                results[torrent_hash] = success
            except Exception as e:
                error(f"暂停下载任务出错: {e}")
                results[torrent_hash] = False
        return results

    @retry_on_connection_error(max_retries=3)
    def batch_resume_downloads(self, torrent_hashes: List[str]) -> Dict[str, bool]:
        results = {}
        for torrent_hash in torrent_hashes:
            try:
                success = self.resume_download(torrent_hash)
                results[torrent_hash] = success
            except Exception as e:
                error(f"恢复下载任务出错: {e}")
                results[torrent_hash] = False
        return results

    @retry_on_connection_error(max_retries=3)
    def batch_remove_downloads(self, torrent_hashes: List[str], delete_files: bool = False) -> Dict[str, bool]:
        results = {}
        for torrent_hash in torrent_hashes:
            try:
                success = self.remove_download(torrent_hash, delete_files)
                results[torrent_hash] = success
            except Exception as e:
                error(f"删除下载任务出错: {e}")
                results[torrent_hash] = False
        return results

    @retry_on_connection_error(max_retries=2)
    def get_client_status(self) -> dict:
        stats = self.get_download_stats()
        return {
            'client_type': self.client_type,
            'connection_status': 'connected' if self.client else 'disconnected',
            'download_limit': self.speed_limit,
            'current_stats': stats,
            'disk_cache': self._get_disk_cache_info(),
            'network_status': self._get_network_status()
        }

    @retry_on_connection_error(max_retries=2)
    def _get_disk_cache_info(self) -> dict:
        try:
            if self.client_type == DownloadClientEnum.QBITTORRENT.value:
                app_info = self.client.app.preferences
                return {
                    'disk_cache': app_info.disk_cache,
                    'disk_cache_ttl': app_info.disk_cache_ttl
                }
            return {}
        except Exception as e:
            error(f"获取磁盘缓存信息失败: {str(e)}")
            return {}

    @retry_on_connection_error(max_retries=2)
    def _get_network_status(self) -> dict:
        try:
            total_speed = self.get_total_speed()
            active_downloads = self.get_active_downloads()
            return {
                'total_download_speed': total_speed,
                'active_connections': sum(t.num_peers for t in active_downloads),
                'total_seeds': sum(t.num_seeds for t in active_downloads)
            }
        except Exception as e:
            error(f"获取网络状态失败: {str(e)}")
            return {}

    @retry(max_retries=3, delay=2.0, backoff=1.5, jitter=True)
    def retry_failed_downloads(self, max_retries: int = 3) -> Dict[str, bool]:
        failed_downloads = self.get_error_downloads()
        results = {}

        for torrent in failed_downloads:
            try:
                retry_count = self._retry_counts.get(torrent.hash, 0)
                if retry_count >= max_retries:
                    results[torrent.hash] = False
                    continue

                self.pause_download(torrent.hash)
                self.resume_download(torrent.hash)
                self._retry_counts[torrent.hash] = retry_count + 1

                results[torrent.hash] = True
            except Exception as e:
                error(f"重试下载任务出错: {e}")
                results[torrent.hash] = False

        return results

    def get_download_speed_history(self, torrent_hash: str, duration: int = 3600) -> List[tuple]:
        current_time = time.time()

        with self._speed_history_lock:
            if torrent_hash not in self._speed_history:
                self._speed_history[torrent_hash] = []

            # 过滤过期数据
            self._speed_history[torrent_hash] = [
                (t, s) for t, s in self._speed_history[torrent_hash]
                if current_time - t <= duration
            ]

            return self._speed_history[torrent_hash].copy()  # 返回副本避免并发修改

    def update_speed_history(self):
        current_time = time.time()
        active_downloads = self.get_active_downloads()

        with self._speed_history_lock:
            for torrent in active_downloads:
                if torrent.hash not in self._speed_history:
                    self._speed_history[torrent.hash] = []
                self._speed_history[torrent.hash].append(
                    (current_time, torrent.download_speed)
                )

    @retry(max_retries=30, delay=1.0, backoff=2.0,
           on_retry=lambda e, count, delay: error(f"添加下载任务失败，重试中 ({count}/3): {str(e)}"))
    def add_download(self, magnet: str, save_path: Optional[str] = None) -> bool:
        """添加下载任务，带重试机制"""
        return self.client.add_torrent(magnet, save_path)

    @retry_on_connection_error()
    def remove_download(self, torrent_hash: str, delete_files: bool = False) -> bool:
        """移除下载任务，带重试机制"""
        return self.client.remove_torrent(torrent_hash, delete_files)

    @retry_on_connection_error()
    def pause_download(self, torrent_hash: str) -> bool:
        return self.client.pause_torrent(torrent_hash)

    @retry_on_connection_error()
    def resume_download(self, torrent_hash: str) -> bool:
        return self.client.resume_torrent(torrent_hash)

    @retry_on_connection_error(max_retries=3)
    def get_download_info(self, torrent_hash: str) -> Optional[TorrentInfo]:
        return self.client.get_torrent_info(torrent_hash)

    @retry_on_connection_error(max_retries=10)
    def get_all_downloads(self) -> List[TorrentInfo]:
        return self.client.get_all_torrents()

    def get_total_speed(self) -> int:
        return sum(t.download_speed for t in self.get_all_downloads())

    @retry_on_connection_error(max_retries=3)
    def get_torrent_speed(self, torrent_hash: str) -> int:
        torrent = self.get_download_info(torrent_hash)
        return torrent.download_speed if torrent else 0

    def is_speed_limit_exceeded(self) -> bool:
        return self.get_total_speed() > self.speed_limit

    def is_torrent_speed_exceeded(self, torrent_hash: str) -> bool:
        return self.get_torrent_speed(torrent_hash) > self.speed_limit

    def set_speed_limit(self, limit_bytes: int) -> None:
        if limit_bytes <= 0:
            raise ValueError("速度限制必须大于0")
        self.speed_limit = limit_bytes

    def get_downloads_by_status(self, status: DownloadStatus) -> List[TorrentInfo]:
        return [t for t in self.get_all_downloads() if t.status == status]

    def get_completed_downloads(self) -> List[TorrentInfo]:
        return self.get_downloads_by_status(DownloadStatus.COMPLETED)

    def get_active_downloads(self) -> List[TorrentInfo]:
        return self.get_downloads_by_status(DownloadStatus.DOWNLOADING)

    def get_queued_downloads(self) -> List[TorrentInfo]:
        return self.get_downloads_by_status(DownloadStatus.QUEUED)

    def get_paused_downloads(self) -> List[TorrentInfo]:
        return self.get_downloads_by_status(DownloadStatus.PAUSED)

    def get_error_downloads(self) -> List[TorrentInfo]:
        return self.get_downloads_by_status(DownloadStatus.ERROR)

    def get_download_stats(self) -> dict:
        downloads = self.get_all_downloads()
        return {
            'total_count': len(downloads),
            'downloading_count': len([t for t in downloads if t.status == DownloadStatus.DOWNLOADING]),
            'completed_count': len([t for t in downloads if t.status == DownloadStatus.COMPLETED]),
            'paused_count': len([t for t in downloads if t.status == DownloadStatus.PAUSED]),
            'error_count': len([t for t in downloads if t.status == DownloadStatus.ERROR]),
            'total_speed': self.get_total_speed(),
            'total_size': sum(t.size for t in downloads),
            'total_downloaded': sum(t.downloaded for t in downloads)
        }

    @retry_on_connection_error()
    def get_download_status(self, name: str = None, hash: str = None) -> int:
        if name is None and hash is None:
            raise ValueError("必须提供name或hash参数之一")
        try:
            torrent = self.get_torrent_by_hash(hash) if hash else self.get_torrent_by_name(name)
            return torrent.status if torrent else DownloadStatus.DOWNLOAD_FAILED
        except Exception as e:
            error(f"查询种子下载状态失败: {str(e)}")
            return DownloadStatus.DOWNLOAD_FAILED

    def get_torrent_by_name(self, name: str) -> Optional[TorrentInfo]:
        for torrent in self.get_all_downloads():
            if name.lower() in torrent.name.lower():
                return torrent
        return None

    @retry_on_connection_error()
    def get_torrent_by_hash(self, hash: str) -> Optional[TorrentInfo]:
        hash_new = self.magnet_util.extract_hash(input_string=hash)
        return self.client.get_torrent_info_by_hash(hash_new)

    @retry(max_retries=2, delay=1.0, backoff=1.5)
    def check_magnet_availability(self, magnet: str) -> bool:
        try:
            result = self.client.add_torrent(magnet)
            if result:
                # 等待几秒检查是否有连接的peers
                import time
                time.sleep(5)
                hash_value = magnet.split('btih:')[1][:40]
                torrent = self.get_download_info(hash_value)
                if torrent and (torrent.num_seeds > 0 or torrent.num_peers > 0):
                    # 可用时删除测试添加的种子
                    self.remove_download(torrent.hash)
                    return True
            return False
        except Exception as e:
            error(f"检查种子可用性失败: {str(e)}")
            return False

    @retry_on_connection_error()
    def replace_slow_torrent(self, torrent_hash: str, new_magnet: str,
                          min_speed: int = 1024 * 1024) -> bool:
        current_torrent = self.get_download_info(torrent_hash)
        if not current_torrent or not current_torrent.is_slow(min_speed):
            return False

        if not self.check_magnet_availability(new_magnet):
            return False

        current_save_path = current_torrent.save_path
        self.remove_download(torrent_hash, delete_files=False)
        return self.add_download(new_magnet, current_save_path)

    def get_slow_downloads(self, min_speed: int = 1024 * 1024) -> List[TorrentInfo]:
        return [t for t in self.get_active_downloads() if t.is_slow(min_speed)]

    def get_download_progress(self, torrent_hash: str) -> float:
        torrent = self.get_download_info(torrent_hash)
        return torrent.progress * 100 if torrent else 0

    def estimate_completion_time(self, torrent_hash: str) -> Optional[float]:
        torrent = self.get_download_info(torrent_hash)
        if not torrent or torrent.download_speed == 0:
            return None
        remaining_bytes = torrent.size - torrent.downloaded
        return remaining_bytes / torrent.download_speed

    def get_download_efficiency(self, torrent_hash: str) -> Optional[float]:
        torrent = self.get_download_info(torrent_hash)
        if not torrent or torrent.downloaded == 0:
            return None
        return torrent.uploaded / torrent.downloaded
