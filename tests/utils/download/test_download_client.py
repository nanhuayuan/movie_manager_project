import pytest
from pathlib import Path
from unittest.mock import Mock, patch
import unittest
from app.model.db.movie_model import Movie
from app.model.mdfileinfo import MdFileInfo
from app.utils.parser.javdb_parser import JavdbParser
from app.utils.parser.parser_factory import ParserFactory
from app.utils.read_markdown_file.normal_markdown_reader import NormalMarkdownReader

from pycallgraph2 import PyCallGraph
from pycallgraph2.output import GraphvizOutput
from pycallgraph2 import Config
from pycallgraph2 import GlobbingFilter


class TestJavdbParser(unittest.TestCase):
    @pytest.fixture
    def reader(self):
        return JavdbParser()

    def test_parse_movie_details_page(self):
        # 获取所有注册的解析器
        all_parsers = ParserFactory.get_all_parsers()
        print("Registered parsers:", list(all_parsers.keys()))

        # 使用特定解析器
        parser = ParserFactory.get_parser('javdb')
        if parser:
            path = "D:/同步_临时/电影库/NSFS-039-page-2.txt"
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            movie_info = parser.parse_movie_details_page(content)
            print(movie_info)
    def test_parse_search_results(self):

        graphviz = GraphvizOutput()
        graphviz.output_file = 'basic.png'
        config = Config()
        config.max_depth = 5  # 控制最大追踪深度

        # 获取所有注册的解析器
        all_parsers = ParserFactory.get_all_parsers()
        print("Registered parsers:", list(all_parsers.keys()))

        # 使用特定解析器
        parser = ParserFactory.get_parser('javdb')
        with PyCallGraph(output=graphviz, config=config):
            if parser:
                path = "D:/同步_临时/电影库/NSFS-039-search-精简1.txt"
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
                movie_info = parser.parse_search_results(content)
                print(movie_info)

if __name__ == '__main__':
    # 初始化配置
    config = AppConfig()

    # 使用工厂类创建下载客户端
    client_factory = DownloadClientFactory()

    # 创建qBittorrent客户端
    qb_client = client_factory.create_client(
        DownloadClient.QBITTORRENT,
        config.qbittorrent_config
    )

    # 创建BitComet客户端
    bc_client = client_factory.create_client(
        DownloadClient.BITCOMET,
        config.bitcomet_config
    )

    # 创建Transmission客户端
    tr_client = client_factory.create_client(
        DownloadClient.TRANSMISSION,
        config.transmission_config
    )

    # 创建下载服务(以qBittorrent为例)
    download_service = DownloadService(qb_client)

    # 连接到客户端
    if qb_client.connect():
        try:
            # 添加下载任务
            magnet = "magnet:?xt=urn:btih:..."
            if download_service.add_download(magnet, save_path="/downloads/"):
                print("下载任务已添加")

            # 获取所有下载任务信息
            for torrent in download_service.get_all_downloads():
                print(f"名称: {torrent.name}")
                print(f"进度: {torrent.progress_str}")
                print(f"大小: {torrent.size_str}")
                print(f"状态: {torrent.status.name}")
                print("---")

        finally:
            # 断开连接
            qb_client.disconnect()
