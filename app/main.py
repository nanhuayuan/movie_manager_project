# main.py
from flask import Flask
from app.config.log_config import info, error, debug
import os
from app.utils.db_util import init_app
from app import controllers, services
from app.config.app_config import AppConfig
from app.container import Container
from app.controllers.movie_controller import init_app as init_movie_controller
from dependency_injector import containers, providers


def create_app(config_name=None):
    """
    创建并配置Flask应用实例。

    Args:
        config_name (str, optional): 配置环境名称，默认从环境变量获取

    Returns:
        Flask: 配置完成的Flask应用实例
    """
    if config_name is None:
        config_name = os.getenv('APP_ENV', 'dev')
    info(f"正在创建应用实例，运行环境：{config_name}")

    app = Flask(__name__)

    # 加载配置
    config_loader = AppConfig()
    config = config_loader.config

    # 设置依赖注入容器
    container = Container()
    container.config.from_dict(config)
    app.container = container

    # 配置依赖注入关系
    container.wire(modules=[
        controllers.movie_controller,
        services.movie_service,
        services.chart_service
    ])

    # 初始化控制器和数据库
    init_movie_controller(app)
    init_app(app)

    info(f"应用实例创建完成，环境：{config_name}")
    return app


if __name__ == '__main__':
    app = create_app()
    #app.run(debug=True)
    app.run()