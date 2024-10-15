import pytest
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

# 假设这是你的应用工厂函数或者获取 app 和 db 的方法
from app.main import create_app
from app.utils.db_util import get_db, init_app


@pytest.fixture(scope='session')
def app():
    app = create_app()
    return app


@pytest.fixture(scope='session')
def _db(app):
    # 使用应用中已存在的 db 实例
    init_app(app)
    db = get_db()
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

        yield session

        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture
def chart_service():
    from app.services.chart_service import ChartService
    return ChartService()


def test_get_movie_chart_and_chary_type_default(app, session, chart_service):
    with app.app_context():
        charts, chart_type = chart_service.get_movie_chart_and_chary_type()
        flg = chart_service.save_chart_data_to_db_and_cache(md_file_list=charts, chart_type=chart_type)
        assert flg is not None  # 根据实际情况修改断言

# 更多测试用例...
