# download_service.py
from typing import Optional, List
from beans import TorrentInfo, DownloadClient
from download_client import BaseDownloadClient, QBittorrentClient


class DownloadService:
    """下载服务类，处理下载任务的管理和监控"""

    def __init__(self, client: BaseDownloadClient):
        self.client = client
        self.speed_limit = 7 * 1024 * 1024  # 7MB/s默认速度限制

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