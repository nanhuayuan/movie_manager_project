from typing import Optional, Dict, Any

from qbittorrent import Client
import time

from app.utils.download_utils import DownloadUtil
from app.utils.log_util import debug, info, warning, error, critical


class DownloadService:
    def __init__(self):
        self.__class__._instance = self
        self.download_util = DownloadUtil()



    def add_torrent(self, torrent_url: str, save_path: str = None) -> Optional[str]:
        """添加种子任务"""
        try:
            debug(f"Adding torrent: {torrent_url}")
            self.qb_client.download_from_link(torrent_url, savepath=save_path)
            # 等待一段时间，让qBittorrent有时间添加种子
            time.sleep(5)
            #return self.get_torrent_hash(torrent_url)

            return True

        except Exception as e:
            error(f"Failed to add torrent: {str(e)}")
            return None

    def get_download_status(self, torrent_hash: str) -> Dict[str, Any]:
        """获取下载状态"""
        try:
            return self.qb_client.get_torrent(torrent_hash)
        except Exception as e:
            error(f"Failed to get download status: {str(e)}")
            return {}

    def check_download_speed(self, torrent_hash: str, min_speed: int = 100 * 1024) -> bool:  # 最小速度100KB/s
        try:
            torrent = self.client.get_torrent(torrent_hash)
            return torrent['dlspeed'] > min_speed
        except Exception as e:
            error(f"Error checking download speed: {str(e)}")
            return False

    def remove_torrent(self, torrent_hash: str):
        try:
            self.client.delete([torrent_hash])
        except Exception as e:
            error(f"Error removing torrent: {str(e)}")

    def get_torrent_hash(self, magnet):
        torrents = self.client.torrents()
        for torrent in torrents:
            if torrent['magnet_uri'] == magnet:
                return torrent['hash']
        return None
