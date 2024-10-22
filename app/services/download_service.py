# download_service.py
from typing import Optional, List
import logging

from app.utils.download_client import TorrentInfo, DownloadClientEnum, DownloadStatus
from app.utils.download_client import QBittorrentClient, BitCometClient, TransmissionClient
from app.config.app_config import AppConfig

logger = logging.getLogger(__name__)


class DownloadService:
    """下载服务类，处理下载任务的管理和监控"""

    def __init__(self):
        """初始化下载服务，加载配置并创建下载客户端"""
        config_loader = AppConfig()
        self.config = config_loader.get_download_client_config()

        self.host = self.config.get('host', '127.0.0.1')
        self.port = self.config.get('port', 6363)
        self.username = self.config.get('username', 'admin')
        self.password = self.config.get('password', 'adminadmin')
        self.client_type = self.config.get('type', DownloadClientEnum.QBITTORRENT.value)

        # 默认速度限制为 7MB/s
        self.speed_limit = 7 * 1024 * 1024

        # 创建并连接客户端
        self.client = self.create_client()
        self.connect_client()

    def connect_client(self) -> bool:
        """连接下载客户端"""
        try:
            return self.client.connect()
        except Exception as e:
            logger.error(f"连接下载客户端失败: {str(e)}")
            return False

    def create_client(self, host: str = None, port: int = None, username: str = None,
                      password: str = None, client_type: str = None):
        """
        创建下载客户端实例

        Args:
            host: 服务器地址
            port: 端口号
            username: 用户名
            password: 密码
            client_type: 客户端类型

        Returns:
            BaseDownloadClient: 下载客户端实例
        """
        host = host or self.host
        port = port or self.port
        username = username or self.username
        password = password or self.password
        client_type = client_type or self.client_type

        client_map = {
            DownloadClientEnum.QBITTORRENT.value: QBittorrentClient,
            DownloadClientEnum.BITCOMET.value: BitCometClient,
            DownloadClientEnum.TRANSMISSION.value: TransmissionClient
        }

        client_class = client_map.get(client_type)
        if not client_class:
            raise ValueError(f"不支持的下载客户端类型: {client_type}")

        return client_class(
            host=host,
            port=port,
            username=username,
            password=password
        )

    def add_download(self, magnet: str, save_path: Optional[str] = None) -> bool:
        """
        添加下载任务

        Args:
            magnet: 磁力链接
            save_path: 保存路径

        Returns:
            bool: 是否添加成功
        """
        try:
            return self.client.add_torrent(magnet, save_path)
        except Exception as e:
            logger.error(f"添加下载任务失败: {str(e)}")
            return False

    def remove_download(self, torrent_hash: str, delete_files: bool = False) -> bool:
        """
        删除下载任务

        Args:
            torrent_hash: 种子哈希
            delete_files: 是否删除文件

        Returns:
            bool: 是否删除成功
        """
        try:
            return self.client.remove_torrent(torrent_hash, delete_files)
        except Exception as e:
            logger.error(f"删除下载任务失败: {str(e)}")
            return False

    def pause_download(self, torrent_hash: str) -> bool:
        """
        暂停下载任务

        Args:
            torrent_hash: 种子哈希

        Returns:
            bool: 是否暂停成功
        """
        try:
            return self.client.pause_torrent(torrent_hash)
        except Exception as e:
            logger.error(f"暂停下载任务失败: {str(e)}")
            return False

    def resume_download(self, torrent_hash: str) -> bool:
        """
        恢复下载任务

        Args:
            torrent_hash: 种子哈希

        Returns:
            bool: 是否恢复成功
        """
        try:
            return self.client.resume_torrent(torrent_hash)
        except Exception as e:
            logger.error(f"恢复下载任务失败: {str(e)}")
            return False

    def get_download_info(self, torrent_hash: str) -> Optional[TorrentInfo]:
        """
        获取下载任务信息

        Args:
            torrent_hash: 种子哈希

        Returns:
            Optional[TorrentInfo]: 下载任务信息
        """
        return self.client.get_torrent_info(torrent_hash)

    def get_all_downloads(self) -> List[TorrentInfo]:
        """
        获取所有下载任务信息

        Returns:
            List[TorrentInfo]: 下载任务信息列表
        """
        return self.client.get_all_torrents()

    def get_total_speed(self) -> int:
        """
        获取总下载速度

        Returns:
            int: 总下载速度(bytes/s)
        """
        return sum(t.download_speed for t in self.get_all_downloads())

    def is_speed_limit_exceeded(self) -> bool:
        """
        检查是否超过速度限制

        Returns:
            bool: 是否超过限制
        """
        return self.get_total_speed() > self.speed_limit

    def set_speed_limit(self, limit_bytes: int) -> None:
        """
        设置速度限制

        Args:
            limit_bytes: 速度限制(bytes/s)
        """
        if limit_bytes <= 0:
            raise ValueError("速度限制必须大于0")
        self.speed_limit = limit_bytes

    def get_downloads_by_status(self, status: DownloadStatus) -> List[TorrentInfo]:
        """
        获取指定状态的下载任务

        Args:
            status: 下载状态

        Returns:
            List[TorrentInfo]: 指定状态的下载任务列表
        """
        return [t for t in self.get_all_downloads() if t.status == status]

    def get_completed_downloads(self) -> List[TorrentInfo]:
        """获取已完成的下载任务"""
        return self.get_downloads_by_status(DownloadStatus.COMPLETED)

    def get_active_downloads(self) -> List[TorrentInfo]:
        """获取正在下载的任务"""
        return self.get_downloads_by_status(DownloadStatus.DOWNLOADING)