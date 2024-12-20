# app/core/app_factory.py

from app.config.log_config import info, error, debug
import os
from app.utils.db_util import init_app
from app.config.app_config import AppConfig
from app.container import Container
from flask import Flask

def create_app(config_name=None):
    """Application factory"""
    if config_name is None:
        config_name = os.getenv('APP_ENV', 'dev')

    info(f"应用启动，当前环境：{config_name}")
    # 创建Flask应用实例
    app = Flask(__name__)

    config_loader = AppConfig()
    config = config_loader.config

    # 设置依赖注入容器
    container = Container()
    container.config.from_dict(config)

    # 初始化数据库
    init_app(app)

    return app