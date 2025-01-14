# download_service.py
from typing import Optional, List

from app.utils.download_client import TorrentInfo, DownloadClientEnum, DownloadStatus, TaskPriority
from app.utils.download_client import QBittorrentClient, BitCometClient, TransmissionClient
from app.config.app_config import AppConfig
from typing import Optional, List, Callable, Dict
from datetime import datetime, timedelta
import threading
import time
import schedule
from dataclasses import dataclass

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
        self.speed_limit = self.config.get('type', 7 * 1024 * 1024) # 默认 7MB/s
        self.client = self.create_client()
        self.client.connect()

        self._scheduled_tasks: Dict[str, ScheduledTask] = {}
        self._scheduler_thread = None
        self._scheduler_running = False

        # 启动计划任务调度器
        self._start_scheduler()

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

        Args:
            magnets: 磁力链接列表
            save_path: 保存路径

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

        Args:
            max_retries: 最大重试次数

        Returns:
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

    def validate_magnet(self, magnet: str) -> bool:
        """验证磁力链接格式

        Args:
            magnet: 磁力链接

        Returns:
            bool: 是否是有效的磁力链接格式
        """
        try:
            if not magnet.startswith('magnet:?'):
                return False

            # 检查是否包含必要的参数
            if 'xt=urn:btih:' not in magnet:
                return False

            # 检查哈希值格式
            hash_value = magnet.split('btih:')[1].split('&')[0]
            if len(hash_value) not in (32, 40):  # MD5或SHA-1哈希长度
                return False

            return True
        except:
            return False

    def get_download_speed_history(self, torrent_hash: str,
                                   duration: int = 3600) -> List[tuple]:
        """获取下载速度历史

        Args:
            torrent_hash: 种子哈希
            duration: 历史时长(秒)

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

        Args:
            start_time: 开始时间
            end_time: 结束时间

        Returns:
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


    def create_client(self, host: str = None, port: int = None, username: str = None,
                      password: str = None, client_type: str = None):
        """创建下载客户端实例"""
        client_map = {
            DownloadClientEnum.QBITTORRENT.value: QBittorrentClient,
            DownloadClientEnum.BITCOMET.value: BitCometClient,
            DownloadClientEnum.TRANSMISSION.value: TransmissionClient
        }

        client_class = client_map.get(client_type or self.client_type)
        if not client_class:
            raise ValueError(f"不支持的下载客户端类型: {client_type}")

        return client_class(
            host=host or self.host,
            port=port or self.port,
            username=username or self.username,
            password=password or self.password
        )

    def add_download(self, magnet: str, save_path: Optional[str] = None) -> bool:
        """添加下载任务"""
        return self.client.add_torrent(magnet, save_path)

    def remove_download(self, torrent_hash: str, delete_files: bool = False) -> bool:
        """删除下载任务"""
        return self.client.remove_torrent(torrent_hash, delete_files)

    def pause_download(self, torrent_hash: str) -> bool:
        """暂停下载任务"""
        return self.client.pause_torrent(torrent_hash)

    def resume_download(self, torrent_hash: str) -> bool:
        """恢复下载任务"""
        return self.client.resume_torrent(torrent_hash)

    def get_download_info(self, torrent_hash: str) -> Optional[TorrentInfo]:
        """获取下载任务信息"""
        return self.client.get_torrent_info(torrent_hash)

    def get_all_downloads(self) -> List[TorrentInfo]:
        """获取所有下载任务信息"""
        return self.client.get_all_torrents()

    def get_total_speed(self) -> int:
        """获取总下载速度"""
        return sum(t.download_speed for t in self.get_all_downloads())

    def get_torrent_speed(self, torrent_hash: str) -> int:
        """获取指定种子的下载速度

        Args:
            torrent_hash: 种子哈希值

        Returns:
            int: 下载速度(bytes/s)，如果种子不存在返回0
        """
        torrent = self.get_download_info(torrent_hash)
        return torrent.download_speed if torrent else 0

    def is_speed_limit_exceeded(self) -> bool:
        """检查是否超过速度限制"""
        return self.get_total_speed() > self.speed_limit

    def is_torrent_speed_exceeded(self, torrent_hash: str) -> bool:
        """检查指定种子是否超过速度限制

        Args:
            torrent_hash: 种子哈希值

        Returns:
            bool: 是否超过速度限制
        """
        return self.get_torrent_speed(torrent_hash) > self.speed_limit

    def set_speed_limit(self, limit_bytes: int) -> None:
        """设置速度限制"""
        if limit_bytes <= 0:
            raise ValueError("速度限制必须大于0")
        self.speed_limit = limit_bytes

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

    def get_download_stats(self) -> dict:
        """获取下载统计信息"""
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

    def get_download_status(self, serial_number: str) -> int:
        """获取指定的内容的现在状态"""
        pass
    def cleanup_old(self):
        """清理下载服务，断开连接"""
        if self.client:
            self.client.disconnect()

    def get_torrent_by_name(self, movie_name: str) -> Optional[TorrentInfo]:
        """根据电影名称搜索下载任务

        Args:
            movie_name: 电影名称

        Returns:
            Optional[TorrentInfo]: 找到的种子信息，未找到返回None
        """

        aaa = self.client.get_torrent_info_by_name(name=movie_name)
        for torrent in self.get_all_downloads():
            if movie_name.lower() in torrent.name.lower():
                return torrent
        return None

    def check_magnet_availability(self, magnet: str) -> bool:
        """检查磁力链接是否可用

        Args:
            magnet: 磁力链接

        Returns:
            bool: 链接是否可用
        """
        try:
            # 尝试添加种子但不开始下载
            result = self.client.add_torrent(magnet)
            if result:
                # 等待几秒检查是否有连接的peers
                import time
                time.sleep(5)
                torrent = self.get_download_info(magnet.split('btih:')[1][:40])
                if torrent and (torrent.num_seeds > 0 or torrent.num_peers > 0):
                    # 可用时删除测试添加的种子
                    self.remove_download(torrent.hash)
                    return True
            return False
        except:
            return False

    def replace_slow_torrent(self, torrent_hash: str, new_magnet: str,
                             min_speed: int = 1024 * 1024) -> bool:
        """替换下载速度过慢的种子

        Args:
            torrent_hash: 当前种子哈希
            new_magnet: 新的磁力链接
            min_speed: 最低速度限制(bytes/s)，默认1MB/s

        Returns:
            bool: 是否替换成功
        """
        current_torrent = self.get_download_info(torrent_hash)
        if not current_torrent or not current_torrent.is_slow(min_speed):
            return False

        if not self.check_magnet_availability(new_magnet):
            return False

        # 记录当前进度
        current_progress = current_torrent.progress
        current_save_path = current_torrent.save_path

        # 删除旧种子但保留文件
        self.remove_download(torrent_hash, delete_files=False)

        # 添加新种子
        if self.add_download(new_magnet, current_save_path):
            return True

        return False

    def get_slow_downloads(self, min_speed: int = 1024 * 1024) -> List[TorrentInfo]:
        """获取下载速度低于指定值的任务

        Args:
            min_speed: 最低速度限制(bytes/s)，默认1MB/s

        Returns:
            List[TorrentInfo]: 低速下载任务列表
        """
        return [t for t in self.get_active_downloads() if t.is_slow(min_speed)]

    def get_download_progress(self, torrent_hash: str) -> float:
        """获取下载进度百分比

        Args:
            torrent_hash: 种子哈希

        Returns:
            float: 进度百分比(0-100)，未找到返回0
        """
        torrent = self.get_download_info(torrent_hash)
        return torrent.progress * 100 if torrent else 0

    def estimate_completion_time(self, torrent_hash: str) -> Optional[float]:
        """估算剩余下载时间(秒)

        Args:
            torrent_hash: 种子哈希

        Returns:
            Optional[float]: 估算的剩余时间(秒)，无法估算返回None
        """
        torrent = self.get_download_info(torrent_hash)
        if not torrent or torrent.download_speed == 0:
            return None

        remaining_bytes = torrent.size - torrent.downloaded
        return remaining_bytes / torrent.download_speed

    def get_download_efficiency(self, torrent_hash: str) -> Optional[float]:
        """计算下载效率(上传/下载比率)

        Args:
            torrent_hash: 种子哈希

        Returns:
            Optional[float]: 效率比率，未找到返回None
        """
        torrent = self.get_download_info(torrent_hash)
        if not torrent or torrent.downloaded == 0:
            return None
        return torrent.uploaded / torrent.downloaded