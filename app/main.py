from flask import Flask

from app import controllers, services
from app.config.config_app import AppConfig
from app.container import Container
from app.controllers.movie_controller import init_app as init_movie_controller
import yaml
from flask import Flask
from dependency_injector import containers, providers


def create_app():
    """
    创建并配置Flask应用实例。

    这个函数负责:
    1. 创建Flask应用
    2. 加载配置
    3. 设置依赖注入容器
    4. 初始化控制器

    :return: 配置好的Flask应用实例
    """
    # 创建Flask应用实例
    app = Flask(__name__)

    config_loader = AppConfig()
    config = config_loader.config

    # 设置依赖注入容器
    container = Container()
    container.config.from_dict(config)

    # 这一步需要吗？
    app.container = container
    # 注册蓝图
    from controllers.movie_controller import movie_bp
    #from controllers.chart_controller import chart_bp
    app.register_blueprint(movie_bp)
    #app.register_blueprint(chart_bp)


    # 将容器与当前模块的依赖关系连接起来
    container.wire(modules=[
        controllers.movie_controller,
        #controllers.chart_controller,
        services.movie_service,
        services.chart_service
    ])

    # 初始化电影控制器
    # 如果`init_movie_controller`是必需的，请确保其实现
    # 否则，可以考虑移除此行
    init_movie_controller(app)

    return app


if __name__ == '__main__':
    # 创建应用并运行
    app = create_app()
    app.run(debug=True)  # 在生产环境中，应该设置debug=False