# download_client.py
from abc import ABC, abstractmethod
from typing import List, Optional, Dict
import qbittorrentapi
from qbittorrent import Client as QBClient
import transmissionrpc
import requests
from app.utils.download.bean.torrent_info import TorrentInfo


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
        except Exception:
            return False

    def disconnect(self) -> None:
        if self.client:
            self.client.auth_log_out()
            self.client = None

    def add_torrent(self, magnet: str, save_path: Optional[str] = None) -> bool:
        try:
            options = {}
            if save_path:
                options['save_path'] = save_path
            return self.client.torrents_add(urls=magnet, **options) == "Ok."
        except Exception:
            return False

    def remove_torrent(self, torrent_hash: str, delete_files: bool = False) -> bool:
        try:
            self.client.torrents_delete(delete_files=delete_files, torrent_hashes=torrent_hash)
            return True
        except Exception:
            return False

    def pause_torrent(self, torrent_hash: str) -> bool:
        try:
            self.client.torrents_pause(torrent_hashes=torrent_hash)
            return True
        except Exception:
            return False

    def resume_torrent(self, torrent_hash: str) -> bool:
        try:
            self.client.torrents_resume(torrent_hashes=torrent_hash)
            return True
        except Exception:
            return False

    def get_torrent_info(self, torrent_hash: str) -> Optional[TorrentInfo]:
        try:
            torrent = self.client.torrents_info(torrent_hashes=torrent_hash)[0]
            return self._convert_to_torrent_info(torrent)
        except Exception:
            return None

    def get_all_torrents(self) -> List[TorrentInfo]:
        try:
            return [self._convert_to_torrent_info(t) for t in self.client.torrents_info()]
        except Exception:
            return []

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


# 在download_client.py中添加BitComet和Transmission的实现:

class BitCometClient(BaseDownloadClient):
    """BitComet客户端实现"""

    def __init__(self, host: str, port: int, username: str, password: str):
        self.base_url = f"http://{host}:{port}"
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.session.auth = (username, password)
        self.connected = False

    def connect(self) -> bool:
        try:
            response = self.session.get(f"{self.base_url}/panel/info")
            self.connected = response.status_code == 200
            return self.connected
        except Exception:
            self.connected = False
            return False

    def disconnect(self) -> None:
        if self.connected:
            self.session.close()
            self.connected = False

    def add_torrent(self, magnet: str, save_path: Optional[str] = None) -> bool:
        try:
            data = {'url': magnet}
            if save_path:
                data['savepath'] = save_path
            response = self.session.post(f"{self.base_url}/panel/add_task", data=data)
            return response.status_code == 200
        except Exception:
            return False

    def remove_torrent(self, torrent_hash: str, delete_files: bool = False) -> bool:
        try:
            params = {
                'hash': torrent_hash,
                'delete_files': '1' if delete_files else '0'
            }
            response = self.session.post(f"{self.base_url}/panel/remove_task", params=params)
            return response.status_code == 200
        except Exception:
            return False

    def pause_torrent(self, torrent_hash: str) -> bool:
        try:
            response = self.session.post(f"{self.base_url}/panel/pause_task", data={'hash': torrent_hash})
            return response.status_code == 200
        except Exception:
            return False

    def resume_torrent(self, torrent_hash: str) -> bool:
        try:
            response = self.session.post(f"{self.base_url}/panel/resume_task", data={'hash': torrent_hash})
            return response.status_code == 200
        except Exception:
            return False

    def get_torrent_info(self, torrent_hash: str) -> Optional[TorrentInfo]:
        try:
            response = self.session.get(f"{self.base_url}/panel/task_info", params={'hash': torrent_hash})
            if response.status_code == 200:
                task_info = response.json()
                return self._convert_to_torrent_info(task_info)
            return None
        except Exception:
            return None

    def get_all_torrents(self) -> List[TorrentInfo]:
        try:
            response = self.session.get(f"{self.base_url}/panel/task_list")
            if response.status_code == 200:
                tasks = response.json()
                return [self._convert_to_torrent_info(task) for task in tasks]
            return []
        except Exception:
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
            # 测试连接
            self.client.session_stats()
            return True
        except Exception:
            return False

    def disconnect(self) -> None:
        if self.client:
            self.client = None

    def add_torrent(self, magnet: str, save_path: Optional[str] = None) -> bool:
        try:
            kwargs = {}
            if save_path:
                kwargs['download_dir'] = save_path
            self.client.add_torrent(magnet, **kwargs)
            return True
        except Exception:
            return False

    def remove_torrent(self, torrent_hash: str, delete_files: bool = False) -> bool:
        try:
            self.client.remove_torrent(torrent_hash, delete_data=delete_files)
            return True
        except Exception:
            return False

    def pause_torrent(self, torrent_hash: str) -> bool:
        try:
            self.client.stop_torrent(torrent_hash)
            return True
        except Exception:
            return False

    def resume_torrent(self, torrent_hash: str) -> bool:
        try:
            self.client.start_torrent(torrent_hash)
            return True
        except Exception:
            return False

    def get_torrent_info(self, torrent_hash: str) -> Optional[TorrentInfo]:
        try:
            torrent = self.client.get_torrent(torrent_hash)
            return self._convert_to_torrent_info(torrent)
        except Exception:
            return None

    def get_all_torrents(self) -> List[TorrentInfo]:
        try:
            return [self._convert_to_torrent_info(t) for t in self.client.get_torrents()]
        except Exception:
            return []

    def _convert_to_torrent_info(self, torrent) -> TorrentInfo:
        """转换Transmission的种子信息为通用格式"""
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
            magnet_uri=torrent.magnetLink if hasattr(torrent, 'magnetLink') else None
        )