# download_service.py
from typing import Optional, List

from app.model.enums import DownloadStatus
from app.utils.download_client import TorrentInfo, DownloadClientEnum
from app.utils.download_client import QBittorrentClient

from app.config.app_config import AppConfig
from app.utils.download_client import BitCometClient, TransmissionClient


class DownloadService:
    """下载服务类，处理下载任务的管理和监控"""

    def __init__(self):
        config_loader = AppConfig()
        self.config = config_loader.get_download_client_config()

        # 使用字典的 get 方法设定默认值
        self.host = self.config.get('host', '127.0.0.1')
        self.port = self.config.get('port', 6363)
        self.username = self.config.get('username', 'admin')
        self.password = self.config.get('password', 'adminadmin')
        self.client_type = self.config.get('type', DownloadClientEnum.QBITTORRENT)  # 设置默认类型

        self.speed_limit = 7 * 1024 * 1024  # 7MB/s 默认速度限制

        # 创建客户端
        self.client = self.create_client()

    def create_client(self, host: str = None, port: int = None, username: str = None, password: str = None, client_type: str = None):
        # 如果没有传入参数，则使用实例中的属性
        host = host or self.host
        port = port or self.port
        username = username or self.username
        password = password or self.password
        client_type = client_type or self.client_type

        if client_type == DownloadClientEnum.QBITTORRENT.value:
            return QBittorrentClient(
                host=host,
                port=port,
                username=username,
                password=password
            )
        elif client_type == DownloadClientEnum.BITCOMET.value:
            return BitCometClient(
                host=host,
                port=port,
                username=username,
                password=password
            )
        elif client_type == DownloadClientEnum.TRANSMISSION.value:
            return TransmissionClient(
                host=host,
                port=port,
                username=username,
                password=password
            )
        else:
            raise ValueError(f"不支持的下载客户端类型: {client_type}")

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
        """获取下载信息"""
        return self.client.get_torrent_info(torrent_hash)

    def get_all_downloads(self) -> List[TorrentInfo]:
        """获取所有下载任务信息"""
        return self.client.get_all_torrents()

    def get_total_speed(self) -> int:
        """获取总下载速度"""
        return sum(t.download_speed for t in self.get_all_downloads())

    def is_speed_limit_exceeded(self) -> bool:
        """检查是否超过速度限制"""
        return self.get_total_speed() > self.speed_limit

    def set_speed_limit(self, limit_bytes: int) -> None:
        """设置速度限制"""
        self.speed_limit = limit_bytes

    def get_completed_downloads(self) -> List[TorrentInfo]:
        """获取已完成的下载"""
        return [t for t in self.get_all_downloads() if t.status == DownloadStatus.COMPLETED]

    def get_active_downloads(self) -> List[TorrentInfo]:
        """获取正在下载的任务"""
        return [t for t in self.get_all_downloads() if t.status == DownloadStatus.DOWNLOADING]

    def get_download_status(self, serial_number):
        return DownloadStatus.COMPLETED.value

    def check_download_speed(self, serial_number):
        pass

    def get_next_magnet(self, serial_number, magnets):
        pass