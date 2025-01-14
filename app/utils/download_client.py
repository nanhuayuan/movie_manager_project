# download_client.py
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum, IntEnum
from typing import List
from typing import Optional

import qbittorrentapi
import requests
import transmissionrpc
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum, IntEnum
from typing import List, Optional, Callable, Dict
from datetime import datetime

class DownloadStatus(IntEnum):
    """
    表示电影或资源的下载状态。

    主要用于 movie 表的 download_status 字段，表示榜单中电影的下载进度。
    """
    NOT_CRAWLED = 0  # 未爬取
    CRAWLED = 1  # 已爬取相关信息，但尚未开始下载
    CRAWL_FAILED = 2  # 爬取信息失败
    DOWNLOAD_FAILED = 3  # 下载失败
    ERROR = 4  # 下载错误
    QUEUED = 5  # 队列中
    CHECKING = 6  # 检查中
    ALLOCATING = 7  # 分配空间
    DOWNLOADING = 8  # 正在下载中
    PAUSED = 9  # 已暂停
    COMPLETED = 10  # 已完成，但可能还未加入媒体库
    IN_LIBRARY = 11  # 已加入媒体库
    NO_SOURCE = 12  # 资源不存在
    OTHER = 13  # 其他状态或特殊情况

class DownloadClientEnum(Enum):
    """下载客户端类型枚举"""
    QBITTORRENT = "qBittorrent"
    BITCOMET = "BitComet"
    TRANSMISSION = "Transmission"  # 新增支持


@dataclass
class TorrentInfo:
    """种子信息基础类"""
    hash: str  # 种子哈希
    name: str  # 种子名称
    size: int  # 总大小(bytes)
    progress: float  # 进度(0-1)
    download_speed: int  # 下载速度(bytes/s)
    upload_speed: int  # 上传速度(bytes/s)
    status: DownloadStatus  # 下载状态
    save_path: str  # 保存路径
    downloaded: int  # 已下载大小(bytes)
    uploaded: int  # 已上传大小(bytes)
    num_seeds: int  # 种子数
    num_peers: int  # 连接节点数
    magnet_uri: Optional[str]  # 磁力链接

    @property
    def progress_str(self) -> str:
        """获取进度百分比字符串"""
        return f"{self.progress * 100:.2f}%"

    @property
    def size_str(self) -> str:
        """获取大小的人类可读形式"""
        units = ['B', 'KB', 'MB', 'GB', 'TB']
        size = float(self.size)
        unit_index = 0
        while size >= 1024 and unit_index < len(units) - 1:
            size /= 1024
            unit_index += 1
        return f"{size:.2f} {units[unit_index]}"
    @property
    def speed_str(self) -> str:
        """获取下载速度的人类可读形式"""
        return self._format_speed(self.download_speed)

    @property
    def upload_speed_str(self) -> str:
        """获取上传速度的人类可读形式"""
        return self._format_speed(self.upload_speed)

    def _format_speed(self, speed: int) -> str:
        """格式化速度为人类可读形式"""
        units = ['B/s', 'KB/s', 'MB/s', 'GB/s']
        unit_index = 0
        speed_float = float(speed)
        while speed_float >= 1024 and unit_index < len(units) - 1:
            speed_float /= 1024
            unit_index += 1
        return f"{speed_float:.2f} {units[unit_index]}"

    def is_slow(self, min_speed: int) -> bool:
        """检查下载速度是否低于指定值"""
        return self.download_speed < min_speed

@dataclass
class DownloadHistory:
    """下载历史记录"""
    torrent_hash: str
    name: str
    start_time: datetime
    end_time: Optional[datetime]
    final_status: DownloadStatus
    downloaded_bytes: int
    average_speed: float
    error_message: Optional[str]

@dataclass
class SourceInfo:
    """资源源信息"""
    url: str
    priority: int
    health_score: float
    last_check_time: datetime
    success_count: int
    fail_count: int
    average_speed: float

class TaskPriority(IntEnum):
    """下载任务优先级"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4

class BaseDownloadClient(ABC):
    """下载客户端基类"""
    def __init__(self):
        self._callbacks: Dict[str, List[Callable]] = {
            'on_complete': [],
            'on_error': [],
            'on_progress': []
        }
        self._history: List[DownloadHistory] = []
        self._sources: Dict[str, SourceInfo] = {}
    @abstractmethod
    def connect(self) -> bool:
        """连接到下载客户端"""
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """断开连接"""
        pass

    @abstractmethod
    def add_torrent(self, magnet: str, save_path: Optional[str] = None) -> bool:
        """添加种子任务"""
        pass

    @abstractmethod
    def remove_torrent(self, torrent_hash: str, delete_files: bool = False) -> bool:
        """删除种子任务"""
        pass

    @abstractmethod
    def pause_torrent(self, torrent_hash: str) -> bool:
        """暂停种子任务"""
        pass

    @abstractmethod
    def resume_torrent(self, torrent_hash: str) -> bool:
        """恢复种子任务"""
        pass

    @abstractmethod
    def get_torrent_info(self, torrent_hash: str) -> Optional[TorrentInfo]:
        """获取种子信息"""
        pass

    @abstractmethod
    def get_torrent_info_by_name(self, name: str) -> Optional[TorrentInfo]:
        """根据名称取种子信息"""
        pass

    @abstractmethod
    def get_all_torrents(self) -> List[TorrentInfo]:
        """获取所有种子信息"""
        pass

    @abstractmethod
    def set_download_limit(self, limit: int) -> bool:
        """设置下载速度限制"""
        pass

    @abstractmethod
    def set_upload_limit(self, limit: int) -> bool:
        """设置上传速度限制"""
        pass

    @abstractmethod
    def get_download_limit(self) -> int:
        """获取下载速度限制"""
        pass

    @abstractmethod
    def get_upload_limit(self) -> int:
        """获取上传速度限制"""
        pass



    @abstractmethod
    def set_task_priority(self, torrent_hash: str, priority: TaskPriority) -> bool:
        """设置任务优先级"""
        pass

    @abstractmethod
    def get_task_priority(self, torrent_hash: str) -> TaskPriority:
        """获取任务优先级"""
        pass

    def add_callback(self, event_type: str, callback: Callable) -> None:
        """添加事件回调

        Args:
            event_type: 事件类型('on_complete', 'on_error', 'on_progress')
            callback: 回调函数
        """
        if event_type in self._callbacks:
            self._callbacks[event_type].append(callback)

    def remove_callback(self, event_type: str, callback: Callable) -> None:
        """移除事件回调"""
        if event_type in self._callbacks and callback in self._callbacks[event_type]:
            self._callbacks[event_type].remove(callback)

    def _trigger_callbacks(self, event_type: str, *args, **kwargs) -> None:
        """触发事件回调"""
        for callback in self._callbacks.get(event_type, []):
            try:
                callback(*args, **kwargs)
            except Exception as e:
                print(f"Callback error: {e}")

    def add_download_history(self, torrent_info: TorrentInfo,
                             end_time: datetime = None,
                             error_msg: str = None) -> None:
        """添加下载历史记录"""
        history = DownloadHistory(
            torrent_hash=torrent_info.hash,
            name=torrent_info.name,
            start_time=datetime.now(),
            end_time=end_time,
            final_status=torrent_info.status,
            downloaded_bytes=torrent_info.downloaded,
            average_speed=torrent_info.download_speed,
            error_message=error_msg
        )
        self._history.append(history)

    def get_download_history(self, days: int = None) -> List[DownloadHistory]:
        """获取下载历史记录

        Args:
            days: 获取最近几天的记录，None表示获取所有
        """
        if days is None:
            return self._history

        cutoff_time = datetime.now().timestamp() - days * 86400
        return [h for h in self._history if h.start_time.timestamp() > cutoff_time]

    def add_source(self, url: str, priority: int = 1) -> None:
        """添加资源源

        Args:
            url: 源地址
            priority: 优先级(1-10)
        """
        if url not in self._sources:
            self._sources[url] = SourceInfo(
                url=url,
                priority=priority,
                health_score=1.0,
                last_check_time=datetime.now(),
                success_count=0,
                fail_count=0,
                average_speed=0
            )

    def update_source_stats(self, url: str, success: bool, speed: float = 0) -> None:
        """更新源统计信息"""
        if url in self._sources:
            source = self._sources[url]
            if success:
                source.success_count += 1
                source.average_speed = (source.average_speed * (
                            source.success_count - 1) + speed) / source.success_count
            else:
                source.fail_count += 1

            # 更新健康度分数
            total = source.success_count + source.fail_count
            source.health_score = source.success_count / total if total > 0 else 0
            source.last_check_time = datetime.now()

    def get_best_source(self) -> Optional[str]:
        """获取最佳源"""
        if not self._sources:
            return None

        return max(self._sources.items(),
                   key=lambda x: (x[1].priority, x[1].health_score, x[1].average_speed))[0]

    def cleanup_sources(self, min_health_score: float = 0.3) -> None:
        """清理不健康的源"""
        for url in list(self._sources.keys()):
            if self._sources[url].health_score < min_health_score:
                del self._sources[url]

class QBittorrentClient(BaseDownloadClient):
    """qBittorrent客户端实现"""

    def __init__(self, host: str, port: int, username: str, password: str):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.client = None

    def connect(self) -> bool:
        try:
            self.client = qbittorrentapi.Client(
                host=f"{self.host}:{self.port}",
                username=self.username,
                password=self.password
            )
            self.client.auth_log_in()
            return True
        except:
            return False

    def disconnect(self) -> None:
        if self.client:
            self.client.auth_log_out()
            self.client = None

    def add_torrent(self, magnet: str, save_path: Optional[str] = None) -> bool:
        if save_path:
            return self.client.torrents_add(urls=magnet, save_path=save_path) == "Ok."
        return self.client.torrents_add(urls=magnet) == "Ok."

    def remove_torrent(self, torrent_hash: str, delete_files: bool = False) -> bool:
        return self.client.torrents_delete(delete_files=delete_files, torrent_hashes=torrent_hash)

    def pause_torrent(self, torrent_hash: str) -> bool:
        return self.client.torrents_pause(torrent_hashes=torrent_hash)

    def resume_torrent(self, torrent_hash: str) -> bool:
        return self.client.torrents_resume(torrent_hashes=torrent_hash)

    def get_torrent_info(self, torrent_hash: str) -> Optional[TorrentInfo]:
        torrent = self.client.torrents_info(torrent_hashes=torrent_hash)[0]
        return self._convert_to_torrent_info(torrent)

    def get_torrent_info_by_name(self, name: str) -> Optional[TorrentInfo]:

        search_job = self.client.search.start(pattern=name, plugins="all", category="all")
        status = search_job.status()
        results = search_job.result()
        search_job.delete()
        print(results)
        #torrent = self.client.torrents_info(torrent_hashes=torrent_hash)[0]
        return self._convert_to_torrent_info(results)

    def get_all_torrents(self) -> List[TorrentInfo]:
        return [self._convert_to_torrent_info(t) for t in self.client.torrents_info()]

    def _convert_to_torrent_info(self, torrent) -> TorrentInfo:
        """转换qBittorrent的种子信息为通用格式"""
        status_map = {
            'downloading': DownloadStatus.DOWNLOADING,
            'stalledDL': DownloadStatus.DOWNLOADING,
            'uploading': DownloadStatus.COMPLETED,
            'stalledUP': DownloadStatus.COMPLETED,
            'pausedDL': DownloadStatus.PAUSED,
            'pausedUP': DownloadStatus.PAUSED,
            'queuedDL': DownloadStatus.QUEUED,
            'queuedUP': DownloadStatus.QUEUED,
            'checking': DownloadStatus.CHECKING,
            'error': DownloadStatus.ERROR
        }

        return TorrentInfo(
            hash=torrent.hash,
            name=torrent.name,
            size=torrent.size,
            progress=torrent.progress,
            download_speed=torrent.dlspeed,
            upload_speed=torrent.upspeed,
            status=status_map.get(torrent.state, DownloadStatus.ERROR),
            save_path=torrent.save_path,
            downloaded=torrent.downloaded,
            uploaded=torrent.uploaded,
            num_seeds=torrent.num_seeds,
            num_peers=torrent.num_peers,
            magnet_uri=torrent.magnet_uri
        )

    # 已有的方法保持不变...

    def set_download_limit(self, limit: int) -> bool:
        try:
            self.client.transfer_set_download_limit(limit)
            return True
        except:
            return False

    def set_upload_limit(self, limit: int) -> bool:
        try:
            self.client.transfer_set_upload_limit(limit)
            return True
        except:
            return False

    def get_download_limit(self) -> int:
        try:
            return self.client.transfer_download_limit()
        except:
            return 0

    def get_upload_limit(self) -> int:
        try:
            return self.client.transfer_upload_limit()
        except:
            return 0

    def set_task_priority(self, torrent_hash: str, priority: TaskPriority) -> bool:
        try:
            # qBittorrent优先级: 1(低) - 7(高)
            priority_map = {
                TaskPriority.LOW: 1,
                TaskPriority.NORMAL: 4,
                TaskPriority.HIGH: 6,
                TaskPriority.URGENT: 7
            }
            self.client.torrents_set_priority(torrent_hash, priority_map[priority])
            return True
        except:
            return False

    def get_task_priority(self, torrent_hash: str) -> TaskPriority:
        try:
            # 获取qBittorrent优先级并转换
            qb_priority = self.client.torrents_info(torrent_hash)[0].priority
            if qb_priority <= 2:
                return TaskPriority.LOW
            elif qb_priority <= 5:
                return TaskPriority.NORMAL
            elif qb_priority == 6:
                return TaskPriority.HIGH
            else:
                return TaskPriority.URGENT
        except:
            return TaskPriority.NORMAL


class BitCometClient(BaseDownloadClient):
    """BitComet客户端实现"""

    def __init__(self, host: str, port: int, username: str, password: str):
        super().__init__()
        self.base_url = f"http://{host}:{port}"
        self.auth = (username, password)
        self.session = requests.Session()
        self._download_limit = 0
        self._upload_limit = 0

    def connect(self) -> bool:
        try:
            response = self.session.get(f"{self.base_url}/panel/info", auth=self.auth)
            return response.status_code == 200
        except:
            return False

    def disconnect(self) -> None:
        self.session.close()

    def add_torrent(self, magnet: str, save_path: Optional[str] = None) -> bool:
        data = {'url': magnet}
        if save_path:
            data['savepath'] = save_path
        response = self.session.post(f"{self.base_url}/panel/addtask", data=data, auth=self.auth)
        return response.status_code == 200

    def remove_torrent(self, torrent_hash: str, delete_files: bool = False) -> bool:
        data = {'hash': torrent_hash, 'delete_files': int(delete_files)}
        response = self.session.post(f"{self.base_url}/panel/removetask", data=data, auth=self.auth)
        return response.status_code == 200

    def pause_torrent(self, torrent_hash: str) -> bool:
        response = self.session.post(f"{self.base_url}/panel/pausetask", data={'hash': torrent_hash}, auth=self.auth)
        return response.status_code == 200

    def resume_torrent(self, torrent_hash: str) -> bool:
        response = self.session.post(f"{self.base_url}/panel/resumetask", data={'hash': torrent_hash}, auth=self.auth)
        return response.status_code == 200

    def get_torrent_info(self, torrent_hash: str) -> Optional[TorrentInfo]:
        response = self.session.get(f"{self.base_url}/panel/taskinfo", params={'hash': torrent_hash}, auth=self.auth)
        if response.status_code == 200:
            return self._convert_to_torrent_info(response.json())
        return None

    def get_all_torrents(self) -> List[TorrentInfo]:
        response = self.session.get(f"{self.base_url}/panel/tasklist", auth=self.auth)
        if response.status_code == 200:
            return [self._convert_to_torrent_info(task) for task in response.json()]
        return []

    def _convert_to_torrent_info(self, task: dict) -> TorrentInfo:
        """转换BitComet的任务信息为通用格式"""
        status_map = {
            'downloading': DownloadStatus.DOWNLOADING,
            'seeding': DownloadStatus.COMPLETED,
            'paused': DownloadStatus.PAUSED,
            'queued': DownloadStatus.QUEUED,
            'checking': DownloadStatus.CHECKING,
            'error': DownloadStatus.ERROR
        }

        return TorrentInfo(
            hash=task['hash'],
            name=task['name'],
            size=task['size'],
            progress=task['progress'] / 100.0,
            download_speed=task.get('download_speed', 0),
            upload_speed=task.get('upload_speed', 0),
            status=status_map.get(task['status'], DownloadStatus.ERROR),
            save_path=task.get('save_path', ''),
            downloaded=task.get('downloaded', 0),
            uploaded=task.get('uploaded', 0),
            num_seeds=task.get('seeds', 0),
            num_peers=task.get('peers', 0),
            magnet_uri=task.get('magnet_uri', '')
        )

    def set_download_limit(self, limit: int) -> bool:
        """设置下载速度限制"""
        try:
            response = self.session.post(
                f"{self.base_url}/panel/setDownloadLimit",
                data={'limit': limit},
                auth=self.auth
            )
            if response.status_code == 200:
                self._download_limit = limit
                return True
            return False
        except:
            return False

    def set_upload_limit(self, limit: int) -> bool:
        """设置上传速度限制"""
        try:
            response = self.session.post(
                f"{self.base_url}/panel/setUploadLimit",
                data={'limit': limit},
                auth=self.auth
            )
            if response.status_code == 200:
                self._upload_limit = limit
                return True
            return False
        except:
            return False

    def get_download_limit(self) -> int:
        """获取下载速度限制"""
        try:
            response = self.session.get(
                f"{self.base_url}/panel/getDownloadLimit",
                auth=self.auth
            )
            if response.status_code == 200:
                return response.json().get('limit', self._download_limit)
            return self._download_limit
        except:
            return self._download_limit

    def get_upload_limit(self) -> int:
        """获取上传速度限制"""
        try:
            response = self.session.get(
                f"{self.base_url}/panel/getUploadLimit",
                auth=self.auth
            )
            if response.status_code == 200:
                return response.json().get('limit', self._upload_limit)
            return self._upload_limit
        except:
            return self._upload_limit

    def set_task_priority(self, torrent_hash: str, priority: TaskPriority) -> bool:
        """设置任务优先级"""
        try:
            # BitComet优先级: 0(低) - 3(高)
            priority_map = {
                TaskPriority.LOW: 0,
                TaskPriority.NORMAL: 1,
                TaskPriority.HIGH: 2,
                TaskPriority.URGENT: 3
            }
            response = self.session.post(
                f"{self.base_url}/panel/setTaskPriority",
                data={
                    'hash': torrent_hash,
                    'priority': priority_map[priority]
                },
                auth=self.auth
            )
            return response.status_code == 200
        except:
            return False

    def get_task_priority(self, torrent_hash: str) -> TaskPriority:
        """获取任务优先级"""
        try:
            response = self.session.get(
                f"{self.base_url}/panel/getTaskPriority",
                params={'hash': torrent_hash},
                auth=self.auth
            )
            if response.status_code == 200:
                bc_priority = response.json().get('priority', 1)
                # 转换BitComet优先级到通用优先级
                if bc_priority <= 0:
                    return TaskPriority.LOW
                elif bc_priority == 1:
                    return TaskPriority.NORMAL
                elif bc_priority == 2:
                    return TaskPriority.HIGH
                else:
                    return TaskPriority.URGENT
            return TaskPriority.NORMAL
        except:
            return TaskPriority.NORMAL

    def get_torrent_file_list(self, torrent_hash: str) -> List[dict]:
        """获取种子文件列表"""
        try:
            response = self.session.get(
                f"{self.base_url}/panel/getFileList",
                params={'hash': torrent_hash},
                auth=self.auth
            )
            if response.status_code == 200:
                return response.json()
            return []
        except:
            return []

    def set_file_priority(self, torrent_hash: str, file_index: int, priority: int) -> bool:
        """设置文件优先级"""
        try:
            response = self.session.post(
                f"{self.base_url}/panel/setFilePriority",
                data={
                    'hash': torrent_hash,
                    'index': file_index,
                    'priority': priority
                },
                auth=self.auth
            )
            return response.status_code == 200
        except:
            return False

    def get_torrent_peers(self, torrent_hash: str) -> List[dict]:
        """获取种子的peer信息"""
        try:
            response = self.session.get(
                f"{self.base_url}/panel/getPeerList",
                params={'hash': torrent_hash},
                auth=self.auth
            )
            if response.status_code == 200:
                return response.json()
            return []
        except:
            return []

    def get_torrent_trackers(self, torrent_hash: str) -> List[dict]:
        """获取种子的tracker信息"""
        try:
            response = self.session.get(
                f"{self.base_url}/panel/getTrackerList",
                params={'hash': torrent_hash},
                auth=self.auth
            )
            if response.status_code == 200:
                return response.json()
            return []
        except:
            return []


class TransmissionClient(BaseDownloadClient):
    """Transmission客户端实现"""

    def __init__(self, host: str, port: int, username: str, password: str):
        super().__init__()
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.client = None

    def connect(self) -> bool:
        try:
            self.client = transmissionrpc.Client(
                address=self.host,
                port=self.port,
                user=self.username,
                password=self.password
            )
            return True
        except:
            return False

    def disconnect(self) -> None:
        self.client = None

    def add_torrent(self, magnet: str, save_path: Optional[str] = None) -> bool:
        try:
            if save_path:
                self.client.add_torrent(magnet, download_dir=save_path)
            else:
                self.client.add_torrent(magnet)
            return True
        except:
            return False

    def remove_torrent(self, torrent_hash: str, delete_files: bool = False) -> bool:
        try:
            self.client.remove_torrent(torrent_hash, delete_data=delete_files)
            return True
        except:
            return False

    def pause_torrent(self, torrent_hash: str) -> bool:
        try:
            self.client.stop_torrent(torrent_hash)
            return True
        except:
            return False

    def resume_torrent(self, torrent_hash: str) -> bool:
        try:
            self.client.start_torrent(torrent_hash)
            return True
        except:
            return False

    def get_torrent_info(self, torrent_hash: str) -> Optional[TorrentInfo]:
        torrent = self.client.get_torrent(torrent_hash)
        return self._convert_to_torrent_info(torrent)

    def get_all_torrents(self) -> List[TorrentInfo]:
        return [self._convert_to_torrent_info(t) for t in self.client.get_torrents()]

    def _convert_to_torrent_info(self, torrent) -> TorrentInfo:
        status_map = {
            'downloading': DownloadStatus.DOWNLOADING,
            'seeding': DownloadStatus.COMPLETED,
            'stopped': DownloadStatus.PAUSED,
            'check pending': DownloadStatus.QUEUED,
            'checking': DownloadStatus.CHECKING,
            'download pending': DownloadStatus.QUEUED,
            'seed pending': DownloadStatus.QUEUED
        }

        return TorrentInfo(
            hash=torrent.hashString,
            name=torrent.name,
            size=torrent.totalSize,
            progress=torrent.progress / 100.0,
            download_speed=torrent.rateDownload,
            upload_speed=torrent.rateUpload,
            status=status_map.get(torrent.status, DownloadStatus.ERROR),
            save_path=torrent.downloadDir,
            downloaded=torrent.downloadedEver,
            uploaded=torrent.uploadedEver,
            num_seeds=torrent.seeders,
            num_peers=torrent.peersConnected,
            magnet_uri=getattr(torrent, 'magnetLink', None)
        )
    def set_download_limit(self, limit: int) -> bool:
        """设置下载速度限制"""
        try:
            self.client.set_session(speed_limit_down=limit,
                                  speed_limit_down_enabled=True)
            return True
        except:
            return False

    def set_upload_limit(self, limit: int) -> bool:
        """设置上传速度限制"""
        try:
            self.client.set_session(speed_limit_up=limit,
                                  speed_limit_up_enabled=True)
            return True
        except:
            return False

    def get_download_limit(self) -> int:
        """获取下载速度限制"""
        try:
            session = self.client.get_session()
            if session.speed_limit_down_enabled:
                return session.speed_limit_down
            return 0
        except:
            return 0

    def get_upload_limit(self) -> int:
        """获取上传速度限制"""
        try:
            session = self.client.get_session()
            if session.speed_limit_up_enabled:
                return session.speed_limit_up
            return 0
        except:
            return 0

    def set_task_priority(self, torrent_hash: str, priority: TaskPriority) -> bool:
        """设置任务优先级"""
        try:
            # Transmission优先级: -1(低), 0(普通), 1(高)
            priority_map = {
                TaskPriority.LOW: -1,
                TaskPriority.NORMAL: 0,
                TaskPriority.HIGH: 1,
                TaskPriority.URGENT: 1
            }
            self.client.change_torrent(torrent_hash,
                                     bandwidthPriority=priority_map[priority])
            return True
        except:
            return False

    def get_task_priority(self, torrent_hash: str) -> TaskPriority:
        """获取任务优先级"""
        try:
            torrent = self.client.get_torrent(torrent_hash)
            # 转换Transmission优先级到通用优先级
            if torrent.bandwidthPriority == -1:
                return TaskPriority.LOW
            elif torrent.bandwidthPriority == 0:
                return TaskPriority.NORMAL
            else:
                return TaskPriority.HIGH
        except:
            return TaskPriority.NORMAL

    def get_session_stats(self) -> dict:
        """获取会话统计信息"""
        try:
            stats = self.client.session_stats()
            return {
                'download_speed': stats.downloadSpeed,
                'upload_speed': stats.uploadSpeed,
                'active_torrent_count': stats.activeTorrentCount,
                'paused_torrent_count': stats.pausedTorrentCount,
                'total_torrent_count': stats.torrentCount
            }
        except:
            return {}

    def get_torrent_files(self, torrent_hash: str) -> List[dict]:
        """获取种子文件列表"""
        try:
            torrent = self.client.get_torrent(torrent_hash)
            return [{
                'name': f.name,
                'size': f.size,
                'completed': f.completed,
                'priority': f.priority
            } for f in torrent.files()]
        except:
            return []

    def set_file_priority(self, torrent_hash: str, file_id: int, priority: str) -> bool:
        """设置文件优先级"""
        try:
            torrent = self.client.get_torrent(torrent_hash)
            # priority可以是'high', 'normal', 'low', 'skip'
            torrent.file_priority(file_id, priority)
            return True
        except:
            return False

    def get_torrent_peers(self, torrent_hash: str) -> List[dict]:
        """获取种子的peer信息"""
        try:
            torrent = self.client.get_torrent(torrent_hash)
            peers = torrent.peers()
            return [{
                'address': p.address,
                'client_name': p.clientName,
                'progress': p.progress,
                'rate_to_client': p.rateToClient,
                'rate_to_peer': p.rateToPeer
            } for p in peers]
        except:
            return []

    def move_torrent(self, torrent_hash: str, new_location: str) -> bool:
        """移动种子文件到新位置"""
        try:
            torrent = self.client.get_torrent(torrent_hash)
            torrent.move_data(new_location)
            return True
        except:
            return False

    def verify_torrent(self, torrent_hash: str) -> bool:
        """验证种子文件"""
        try:
            torrent = self.client.get_torrent(torrent_hash)
            torrent.verify()
            return True
        except:
            return False

    def get_free_space(self, path: str) -> int:
        """获取指定路径的可用空间"""
        try:
            return self.client.free_space(path)
        except:
            return 0

    def _convert_to_torrent_info(self, torrent) -> TorrentInfo:
        """转换Transmission的种子信息为通用格式"""
        status_map = {
            'stopped': DownloadStatus.PAUSED,
            'check pending': DownloadStatus.QUEUED,
            'checking': DownloadStatus.CHECKING,
            'download pending': DownloadStatus.QUEUED,
            'downloading': DownloadStatus.DOWNLOADING,
            'seed pending': DownloadStatus.QUEUED,
            'seeding': DownloadStatus.COMPLETED
        }

        return TorrentInfo(
            hash=torrent.hashString,
            name=torrent.name,
            size=torrent.totalSize,
            progress=torrent.progress / 100.0,
            download_speed=torrent.downloadSpeed,
            upload_speed=torrent.uploadSpeed,
            status=status_map.get(torrent.status, DownloadStatus.ERROR),
            save_path=torrent.downloadDir,
            downloaded=torrent.downloadedEver,
            uploaded=torrent.uploadedEver,
            num_seeds=torrent.peersSendingToUs,
            num_peers=torrent.peersGettingFromUs,
            magnet_uri=torrent.magnetLink if hasattr(torrent, 'magnetLink') else None
        )