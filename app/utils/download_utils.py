from enum import Enum, IntEnum

import requests
from qbittorrent import Client
from requests.exceptions import RequestException
import time
import random

from app.config.app_config import AppConfig
from app.enum.download_client_enum import DownloadClient
from app.utils.log_util import logger


class DownloadUtil:
    def __init__(self):
        config = AppConfig()
        self.qb_config = config.get_qbittorrent_config()
        self.bc_config = config.get_bitcomet_config()

        self.qbittorrent_url = f"http://{self.qb_config['username']}:{self.qb_config['password']}@{self.qb_config['host']}:{self.qb_config['port']}"
        self.bitcomet_url = f"http://{self.bc_config['username']}:{self.bc_config['password']}@{self.bc_config['host']}:{self.bc_config['port']}"

        self.qb = Client(self.qbittorrent_url)

    def download(self, magnet: str, client: DownloadClient = DownloadClient.QBITTORRENT,download_folder = None) -> bool:
        """
        使用指定的客户端下载电影。
        """
        logger.info(f"开始使用 {client.value} 下载: {magnet}")

        max_retry_attempts = self.qb_config.get('max_retry_attempts', 3) if client == DownloadClient.QBITTORRENT else self.bc_config.get('max_retry_attempts', 3)
        download_folder = self.qb_config.get('download_folder') if client == DownloadClient.QBITTORRENT else self.bc_config.get('download_folder')
        download_folder = None

        for attempt in range(1, max_retry_attempts + 1):

            if client == DownloadClient.QBITTORRENT:
                self.qb.download_from_link(magnet, savepath=download_folder)
            elif client == DownloadClient.BITCOMET:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.159 Safari/537.36',
                }
                data = {
                    'url': magnet,
                    'savepath': download_folder
                }
                response = requests.post(url=self.bitcomet_url, data=data, headers=headers)
                response.raise_for_status()
            else:
                raise ValueError(f"不支持的下载客户端: {client}")

            logger.info(f"{client.value} 下载任务已添加: {magnet}")
            return True


    def get_download_status(self, magnet: str, client: DownloadClient = DownloadClient.QBITTORRENT) -> dict:
        """
        获取下载状态。
        """
        if client == DownloadClient.QBITTORRENT:
            # 实现qBittorrent获取下载状态的逻辑
            pass
        elif client == DownloadClient.BITCOMET:
            # 实现BitComet获取下载状态的逻辑
            pass
        else:
            logger.error(f"不支持的下载客户端: {client}")
            return {}

    def remove_download(self, magnet: str, client: DownloadClient = DownloadClient.QBITTORRENT) -> bool:
        """
        移除下载任务。

        """
        if client == DownloadClient.QBITTORRENT:
            # 实现qBittorrent移除下载任务的逻辑
            pass
        elif client == DownloadClient.BITCOMET:
            # 实现BitComet移除下载任务的逻辑
            pass
        else:
            logger.error(f"不支持的下载客户端: {client}")
            return False

    def get_download_speed(self, name: str, client: DownloadClient = DownloadClient.QBITTORRENT) -> float:
        if client == DownloadClient.QBITTORRENT:
            torrents = self.qb.torrents(name)

        elif client == DownloadClient.BITCOMET:
            return None
        return 0;

    def get_torrents(self, name: str = None, client: DownloadClient = DownloadClient.QBITTORRENT):

        if client == DownloadClient.QBITTORRENT:

            return None

        elif client == DownloadClient.BITCOMET:
            return None

