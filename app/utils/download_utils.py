from qbittorrent import Client
from requests.exceptions import HTTPError
import time
import random

from app.utils.http_util import HttpUtil
from app.utils.log_util import debug, info, warning, error, critical
class DownloadUtils:
    def get_movie_magnet(uri):
        """
        获取电影的磁力链接。

        Args:
            uri (str): 电影页面的URI。

        Returns:
            list: 磁力链接列表。
        """
        url = f'https://javdb.com{uri}'
        info(f"Fetching magnet links for movie: {url}")

        soup = HttpUtil.proxy_request(url)
        magnets_content = soup.find('div', id='magnets-content')

        if not magnets_content:
            warning(f"No magnet links found for: {uri}")
            return []

        magnet_list = [a['href'] for a in magnets_content.find_all('a')]
        debug(f"Found {len(magnet_list)} magnet links")
        return magnet_list


    def download_by_qbittorrent(movie_info, retry_count=1, max_retry_count=10):
        """
        使用qBittorrent下载电影。

        Args:
            movie_info (dict): 包含电影信息的字典。
            retry_count (int, optional): 当前重试次数。默认为1。
            max_retry_count (int, optional): 最大重试次数。默认为10。

        Returns:
            bool: 下载是否成功。
        """
        if not movie_info['magnet_list']:
            warning(f"No magnet links for movie: {movie_info['serial_number']}")
            return False

        magnet = movie_info['magnet_list'][0]
        info(f"Starting download for {movie_info['serial_number']}")

        while retry_count <= max_retry_count:
            try:
                qb = Client('http://192.168.31.45:6363/', verify=False)
                qb.login('admin', 'adminadmin')
                qb.download_from_link(magnet)
                info(f"Download completed for {movie_info['serial_number']}")
                return True
            except (Client.LoginRequired, HTTPError) as e:
                error(f"Download failed (attempt {retry_count}/{max_retry_count}): {e}")
                retry_count += 1
                time.sleep(random.randint(10, 30))

        error(f"Max retries exceeded for {movie_info['serial_number']}")
        return False