# test_download_service.py
import unittest
from unittest.mock import Mock, patch
from app.utils.download_client import TorrentInfo, DownloadClientEnum, DownloadStatus


class TestDownloadService(unittest.TestCase):
    """DownloadService测试类"""

    def setUp(self):
        """测试初始化"""
        self.mock_config = {
            'host': 'test.com',
            'port': 8080,
            'username': 'test_user',
            'password': 'test_pass',
            'type': DownloadClientEnum.QBITTORRENT.value
        }

        with patch('app.config.app_config.AppConfig') as mock_config:
            mock_config.return_value.get_download_client_config.return_value = self.mock_config
            from app.services.download_service import DownloadService
            self.service = DownloadService()

    def test_create_client(self):
        """测试创建客户端"""
        # 测试默认创建
        self.assertIsNotNone(self.service.client)

        # 测试创建不支持的客户端类型
        with self.assertRaises(ValueError):
            self.service.create_client(client_type='UnsupportedClient')

    def test_add_download(self):
        """测试添加下载"""
        self.service.client.add_torrent = Mock(return_value=True)
        result = self.service.add_download("magnet:test", "/save/path")
        self.assertTrue(result)
        self.service.client.add_torrent.assert_called_once_with("magnet:test", "/save/path")

    def test_get_download_info(self):
        """测试获取下载信息"""
        mock_info = TorrentInfo(
            hash="test_hash",
            name="test_torrent",
            size=1000,
            progress=0.5,
            download_speed=1024,
            upload_speed=512,
            status=DownloadStatus.DOWNLOADING,
            save_path="/test/path",
            downloaded=500,
            uploaded=200,
            num_seeds=10,
            num_peers=20,
            magnet_uri="magnet:test"
        )

        self.service.client.get_torrent_info = Mock(return_value=mock_info)
        result = self.service.get_download_info("test_hash")
        self.assertEqual(result, mock_info)
        self.service.client.get_torrent_info.assert_called_once_with("test_hash")

    def test_speed_limit(self):
        """测试速度限制相关功能"""
        # 测试设置速度限制
        self.service.set_speed_limit(1024 * 1024)  # 1MB/s
        self.assertEqual(self.service.speed_limit, 1024 * 1024)

        # 测试设置无效速度限制
        with self.assertRaises(ValueError):
            self.service.set_speed_limit(0)

        # 测试检查速度限制
        mock_torrent = TorrentInfo(
            hash="test",
            name="test",
            size=1000,
            progress=0.5,
            download_speed=2 * 1024 * 1024,  # 2MB/s
            upload_speed=0,
            status=DownloadStatus.DOWNLOADING,
            save_path="/test",
            downloaded=500,
            uploaded=0,
            num_seeds=1,
            num_peers=1,
            magnet_uri=None
        )

        self.service.get_all_downloads = Mock(return_value=[mock_torrent])
        self.assertTrue(self.service.is_speed_limit_exceeded())

    def test_get_downloads_by_status(self):
        """测试按状态获取下载任务"""
        mock_downloads = [
            TorrentInfo(
                hash="test1",
                name="test1",
                size=1000,
                progress=1.0,
                download_speed=0,
                upload_speed=0,
                status=DownloadStatus.COMPLETED,
                save_path="/test",
                downloaded=1000,
                uploaded=500,
                num_seeds=0,
                num_peers=0,
                magnet_uri=None
            ),
            TorrentInfo(
                hash="test2",
                name="test2",
                size=1000,
                progress=0.5,
                download_speed=1024,
                upload_speed=0,
                status=DownloadStatus.DOWNLOADING,
                save_path="/test",
                downloaded=500,
                uploaded=0,
                num_seeds=1,
                num_peers=1,
                magnet_uri=None
            )
        ]

        self.service.get_all_downloads = Mock(return_value=mock_downloads)

        # 测试获取已完成的下载
        completed = self.service.get_completed_downloads()
        self.assertEqual(len(completed), 1)
        self.assertEqual(completed[0].hash, "test1")

        # 测试获取活动的下载
        active = self.service.get_active_downloads()
        self.assertEqual(len(active), 1)
        self.assertEqual(active[0].hash, "test2")


if __name__ == '__main__':
    unittest.main()