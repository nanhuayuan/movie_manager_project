from datetime import datetime, timedelta

import pytest
import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from qbittorrentapi import SearchAPIMixIn

from app.config.log_config import debug, info, warning, error, critical
from app.main import create_app
from app.main_add_chart_to_db import run_scraper
from app.main_add_to_playlists import process_charts
from app.main_remove_duplicate_movies_from_jellyfin import process_duplicates
from app.main_remove_not_exist_locally_in_jellyfin import process_missing_movies
from app.services import DownloadService
from app.utils.db_util import get_db, init_app
from app.utils.download_client import TransmissionClient


@pytest.fixture(scope='session')
def app():
    """
    创建测试用的Flask应用实例

    Returns:
        Flask: 配置好的Flask测试应用实例
    """
    info("正在创建测试用Flask应用实例")
    app = create_app('test')
    info("测试用Flask应用实例创建完成")
    return app


@pytest.fixture(scope='session')
def _db(app):
    """
    初始化测试数据库连接

    Args:
        app: Flask应用实例

    Returns:
        SQLAlchemy: 数据库实例
    """
    info("正在初始化测试数据库连接")
    db = get_db()
    info("测试数据库连接初始化完成")
    return db


@pytest.fixture(scope='function')
def session(app, _db):
    """
    创建测试用数据库会话

    Args:
        app: Flask应用实例
        _db: 数据库实例

    Yields:
        SQLAlchemy.session: 数据库会话实例
    """
    with app.app_context():
        info("正在创建测试用数据库会话")
        connection = _db.engine.connect()
        transaction = connection.begin()

        session = _db.session
        session.bind = connection

        debug("数据库测试会话创建完成")
        yield session

        info("正在清理测试数据库会话")
        session.close()
        transaction.rollback()
        connection.close()
        debug("数据库测试会话已清理完成")


@pytest.fixture
def scraper_service():
    """
    创建爬虫服务实例

    Returns:
        ScraperService: 爬虫服务实例
    """
    from app.services.scraper_service import ScraperService
    debug("正在创建爬虫服务测试实例")
    service = ScraperService()
    return service


def test_add_chart_to_db(app, session, scraper_service):
    """测试添加榜单数据到数据库的功能"""
    with app.app_context():
        info("开始测试：添加榜单数据到数据库")
        result = run_scraper()
        debug(f"处理结果：{result}")


def test_add_to_playlists(app, session, scraper_service):
    """测试添加电影到播放列表的功能"""
    with app.app_context():
        info("开始测试：添加电影到播放列表")
        result = process_charts()
        debug(f"处理结果：{result}")


def test_remove_duplicate_movies(app, session, scraper_service):
    """测试移除重复电影的功能"""
    with app.app_context():
        info("开始测试：移除重复电影")
        result = process_duplicates()
        debug(f"处理结果：{result}")

def test_remove_missing_movies(app, session, scraper_service):
    """测试移除本地不存在电影的功能"""
    with app.app_context():
        info("开始测试：移除本地不存在的电影")
        result = process_missing_movies()
        debug(f"处理结果：{result}")


def test_check_torrent_info(app, session, scraper_service):
    """
    检查种子信息
    Args:
        app:
        session:
        scraper_service:

    Returns:

    """
    with app.app_context():
        info("开始测试：检查种子信息")
        # 创建下载服务实例



        service = DownloadService()

        torrentInfo_bglb = service.get_torrent_by_name('报告老板')

        print(torrentInfo_bglb)


        # 批量添加下载任务
        magnets = ['magnet:?xt=...', 'magnet:?xt=...']
        results = service.batch_add_downloads(magnets, '/downloads')

        # 添加定时任务
        task_id = service.add_scheduled_task(
            torrent_hash='...',
            action='pause',
            schedule_time=datetime.now() + timedelta(hours=2)
        )

        # 导出报告
        report = service.export_task_report()

        # 优化活动任务
        result = service.optimize_active_tasks()

        # 清理资源
        service.cleanup()
        debug(f"处理结果：{result}")

def test_bitcomet_client(app):
    """"""
    with app.app_context():
        info("开始测试：移除本地不存在的电影")
        # BitComet客户端
        bc_client = BitCometClient(
            host='localhost',
            port=6363,
            username='admin',
            password='password'
        )

        # 设置速度限制
        bc_client.set_download_limit(1024 * 1024)  # 1MB/s

        # 获取文件列表
        files = bc_client.get_torrent_file_list("torrent_hash")

        # Transmission客户端
        tr_client = TransmissionClient(
            host='localhost',
            port=9091,
            username='admin',
            password='password'
        )

        # 获取统计信息
        stats = tr_client.get_session_stats()

        # 移动种子文件
        tr_client.move_torrent("torrent_hash", "/new/location")

        # 验证种子文件
        tr_client.verify_torrent("torrent_hash")
        debug(f"处理结果：{result}")

def test_environment_config(app):
    """测试环境配置是否正确"""
    with app.app_context():
        info("开始测试：环境配置检查")
        env = os.getenv('APP_ENV', 'dev')
        debug(f"当前环境配置：{env}")
        # 添加更多环境配置测试