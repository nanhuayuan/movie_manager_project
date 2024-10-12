from qbittorrent import Client
import time
import logging

class QBittorrentService:
    def __init__(self):
        self.__class__._instance = self

    def add_torrent(self, magnet: str) -> str:
        try:
            self.client.download_from_link(magnet)
            # 等待一段时间，让qBittorrent有时间添加种子
            time.sleep(5)
            torrents = self.client.torrents()
            for torrent in torrents:
                if torrent['magnet_uri'] == magnet:
                    return torrent['hash']
            return None
        except Exception as e:
            self.logger.error(f"Error adding torrent: {str(e)}")
            return None

    def check_download_speed(self, torrent_hash: str, min_speed: int = 100 * 1024) -> bool:  # 最小速度100KB/s
        try:
            torrent = self.client.get_torrent(torrent_hash)
            return torrent['dlspeed'] > min_speed
        except Exception as e:
            self.logger.error(f"Error checking download speed: {str(e)}")
            return False

    def remove_torrent(self, torrent_hash: str):
        try:
            self.client.delete([torrent_hash])
        except Exception as e:
            self.logger.error(f"Error removing torrent: {str(e)}")