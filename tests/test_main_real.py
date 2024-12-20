import pytest
import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from app.config.log_config import debug, info, warning, error, critical
from app.main import create_app
from app.main_add_chart_to_db import run_scraper
from app.main_add_to_playlists import process_charts
from app.main_remove_duplicate_movies_from_jellyfin import process_duplicates
from app.main_remove_not_exist_locally_in_jellyfin import process_missing_movies
from app.utils.db_util import get_db, init_app


@pytest.fixture(scope='session')
def app():
    """
    创建测试用的Flask应用实例

    Returns:
        Flask: 配置好的Flask测试应用实例
    """
    info("正在创建测试用Flask应用实例")
    app = create_app()
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


def test_environment_config(app):
    """测试环境配置是否正确"""
    with app.app_context():
        info("开始测试：环境配置检查")
        env = os.getenv('APP_ENV', 'dev')
        debug(f"当前环境配置：{env}")
        # 添加更多环境配置测试