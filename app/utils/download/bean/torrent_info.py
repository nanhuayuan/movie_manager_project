from dataclasses import dataclass
from typing import Optional

from app.model.enums import DownloadStatus


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