# download_client.py
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum, IntEnum
from typing import List
from typing import Optional

import qbittorrentapi
import requests
import transmissionrpc


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


class BaseDownloadClient(ABC):
    """下载客户端基类"""

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
    def get_all_torrents(self) -> List[TorrentInfo]:
        """获取所有种子信息"""
        pass


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


class BitCometClient(BaseDownloadClient):
    """BitComet客户端实现"""

    def __init__(self, host: str, port: int, username: str, password: str):
        self.base_url = f"http://{host}:{port}"
        self.auth = (username, password)
        self.session = requests.Session()

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


class TransmissionClient(BaseDownloadClient):
    """Transmission客户端实现"""

    def __init__(self, host: str, port: int, username: str, password: str):
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
