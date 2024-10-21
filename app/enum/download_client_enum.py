from enum import Enum


class DownloadClient(Enum):
    """下载客户端类型枚举"""
    QBITTORRENT = "qBittorrent"
    BITCOMET = "BitComet"
    TRANSMISSION = "Transmission"  # 新增支持