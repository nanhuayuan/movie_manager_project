# test_download_service.py
import os

import pytest
from unittest.mock import Mock, patch

from app.config.app_config import AppConfig
from app.services import DownloadService
from app.utils.download_client import TorrentInfo, DownloadStatus, DownloadClientEnum


@pytest.fixture
def mock_config():
    """mock配置"""

    os.environ['APP_ENV'] = 'test'
    return AppConfig()



@pytest.fixture
def mock_torrent_info():
    """mock种子信息"""
    # magnet:?xt=urn:btih:90cee4de68ac0362196d082d120fc656cf27bf64
    return TorrentInfo(
        hash='90cee4de68ac0362196d082d120fc656cf27bf64',
        name='win 10.torrent',
        size=1024 * 1024 * 1024 * 6.5,  # 100MB
        progress=0.5,
        download_speed=1024 * 1024,  # 1MB/s
        upload_speed=512 * 1024,  # 512KB/s
        status=DownloadStatus.DOWNLOADING,
        save_path='/downloads',
        downloaded=1024 * 1024 * 50,  # 50MB
        uploaded=1024 * 1024 * 10,  # 10MB
        num_seeds=10,
        num_peers=20,
        magnet_uri='magnet:?xt=test'
    )


@pytest.fixture
def mock_service():
    """mock下载服务"""
    os.environ['APP_ENV'] = 'test'
    return DownloadService()



class TestDownloadService:
    """DownloadService测试类"""

    def test_add_download(self):
        """测试添加下载"""
        service = DownloadService()
        magnet = 'magnet:?xt=urn:btih:90cee4de68ac0362196d082d120fc656cf27bf64'
        save_path = '/downloads'

        result = service.add_download(magnet, save_path)
        print(result)


    def test_remove_download(self, mock_service):
        """测试删除下载"""
        mock_service.client.remove_torrent.return_value = True
        torrent_hash = 'test_hash'

        result = mock_service.remove_download(torrent_hash, True)

        assert result is True
        mock_service.client.remove_torrent.assert_called_once_with(torrent_hash, True)

    def test_get_torrent_speed(self, mock_service, mock_torrent_info):
        """测试获取种子速度"""
        mock_service.client.get_torrent_info.return_value = mock_torrent_info
        torrent_hash = 'test_hash'

        speed = mock_service.get_torrent_speed(torrent_hash)

        assert speed == mock_torrent_info.download_speed
        mock_service.client.get_torrent_info.assert_called_once_with(torrent_hash)

    def test_is_torrent_speed_exceeded(self, mock_service, mock_torrent_info):
        """测试种子速度是否超限"""
        mock_service.client.get_torrent_info.return_value = mock_torrent_info
        torrent_hash = 'test_hash'

        # 设置速度限制为500KB/s
        mock_service.speed_limit = 512 * 1024

        # 种子速度为1MB/s，应该超限
        assert mock_service.is_torrent_speed_exceeded(torrent_hash) is True

        # 设置速度限制为2MB/s
        mock_service.speed_limit = 2 * 1024 * 1024

        # 种子速度为1MB/s，不应该超限
        assert mock_service.is_torrent_speed_exceeded(torrent_hash) is False

    def test_get_downloads_by_status(self, mock_service, mock_torrent_info):
        """测试按状态获取下载"""
        mock_service.client.get_all_torrents.return_value = [
            mock_torrent_info,
            TorrentInfo(**{**mock_torrent_info.__dict__,
                           'hash': 'test_hash2',
                           'status': DownloadStatus.COMPLETED}),
            TorrentInfo(**{**mock_torrent_info.__dict__,
                           'hash': 'test_hash3',
                           'status': DownloadStatus.DOWNLOADING})
        ]

        downloading = mock_service.get_downloads_by_status(DownloadStatus.DOWNLOADING)
        completed = mock_service.get_downloads_by_status(DownloadStatus.COMPLETED)

        assert len(downloading) == 2
        assert len(completed) == 1
        assert all(t.status == DownloadStatus.DOWNLOADING for t in downloading)
        assert all(t.status == DownloadStatus.COMPLETED for t in completed)

    def test_get_download_stats(self, mock_service, mock_torrent_info):
        """测试获取下载统计"""
        mock_service.client.get_all_torrents.return_value = [
            mock_torrent_info,
            TorrentInfo(**{**mock_torrent_info.__dict__,
                           'hash': 'test_hash2',
                           'status': DownloadStatus.COMPLETED}),
            TorrentInfo(**{**mock_torrent_info.__dict__,
                           'hash': 'test_hash3',
                           'status': DownloadStatus.ERROR})
        ]

        stats = mock_service.get_download_stats()

        assert stats['total_count'] == 3
        assert stats['downloading_count'] == 1
        assert stats['completed_count'] == 1
        assert stats['error_count'] == 1
        assert stats['total_speed'] == sum(t.download_speed for t in mock_service.get_all_downloads())
        assert stats['total_size'] == sum(t.size for t in mock_service.get_all_downloads())
        assert stats['total_downloaded'] == sum(t.downloaded for t in mock_service.get_all_downloads())

    def test_cleanup(self, mock_service):
        """测试清理服务"""
        mock_service.cleanup()
        mock_service.client.disconnect.assert_called_once()

    def test_set_speed_limit(self, mock_service):
        """测试设置速度限制"""
        new_limit = 10 * 1024 * 1024  # 10MB/s
        mock_service.set_speed_limit(new_limit)
        assert mock_service.speed_limit == new_limit

        with pytest.raises(ValueError):
            mock_service.set_speed_limit(-1)
            mock_service.set_speed_limit(0)

    @pytest.mark.parametrize("method_name,client_method_name", [
        ('pause_download', 'pause_torrent'),
        ('resume_download', 'resume_torrent'),
        ('get_download_info', 'get_torrent_info'),
        ('get_all_downloads', 'get_all_torrents'),
    ])
    def test_basic_operations(self, mock_service, method_name, client_method_name):
        """测试基本操作方法"""
        client_method = getattr(mock_service.client, client_method_name)
        client_method.return_value = True

        method = getattr(mock_service, method_name)
        result = method('test_hash' if method_name != 'get_all_downloads' else None)

        assert result is True
        if method_name != 'get_all_downloads':
            client_method.assert_called_once_with('test_hash')
        else:
            client_method.assert_called_once_with()