import pytest
import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from app.config.log_config import debug, info, warning, error, critical

# 假设这是你的应用工厂函数或者获取 app 和 db 的方法
from app.main import create_app
from app.utils.db_util import get_db, init_app

@pytest.fixture(scope='session')
def app():
    # 设置测试环境
    os.environ['APP_ENV'] = 'dev'
    app = create_app()
    info("Test Flask app created")
    return app

@pytest.fixture(scope='session')
def _db(app):
    # 使用应用中已存在的 db 实例
    #init_app(app)
    db = get_db()
    info("Test database initialized")
    return db

@pytest.fixture(scope='function')
def session(app, _db):
    with app.app_context():
        connection = _db.engine.connect()
        transaction = connection.begin()

        # 使用 db.session 而不是创建新的 scoped session
        session = _db.session

        # 将会话绑定到这个连接
        session.bind = connection

        debug("Test database session created")
        yield session

        session.close()
        transaction.rollback()
        connection.close()
        debug("Test database session closed and transaction rolled back")

@pytest.fixture
def scraper_service():
    from app.services.scraper_service import ScraperService
    service = ScraperService()
    debug("ScraperService instance created for testing")
    return service

def test_parse_movie_details_page(app, session, scraper_service):
    with app.app_context():
        info("Starting test: processor")
        result = scraper_service.process_all_charts()
        debug(f"processor result: {result}")

# 更多测试用例...

def test_environment_config(app):
    with app.app_context():
        info("Starting test: environment_config")
        assert os.getenv('APP_ENV') == 'test', "APP_ENV should be set to 'test'"
        # 这里可以添加更多针对测试环境配置的断言
        debug("Environment configuration test completed")