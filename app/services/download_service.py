# download_service.py
from typing import Optional, List

from app.utils.download_client import TorrentInfo, DownloadClientEnum, DownloadStatus
from app.utils.download_client import QBittorrentClient, BitCometClient, TransmissionClient
from app.config.app_config import AppConfig

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
    def cleanup(self):
        """清理下载服务，断开连接"""
        if self.client:
            self.client.disconnect()