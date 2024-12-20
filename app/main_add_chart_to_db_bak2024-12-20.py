import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from app.config.log_config import info, error, debug
from app.main import create_app
from app.services.scraper_service import ScraperService
from app.utils.db_util import init_app, get_db


def create_app1(config_name=None):
    """
    应用工厂函数，用于创建和配置Flask应用实例

    Args:
        config_name (str, optional): 配置环境名称。默认为None，将使用环境变量中的配置

    Returns:
        Flask: 配置完成的Flask应用实例
    """
    # 如果没有指定配置名，则从环境变量获取
    if config_name is None:
        config_name = os.getenv('APP_ENV', 'dev')

    # 创建Flask应用实例
    app = Flask(__name__)

    # 根据不同的环境加载配置
    if config_name == 'production':
        app.config.from_object('app.config.production_config')
    elif config_name == 'test':
        app.config.from_object('app.config.test_config')
    else:
        app.config.from_object('app.config.development_config')

    # 初始化数据库
    init_app(app)

    # 记录应用启动信息
    info(f"应用启动，当前环境：{config_name}")

    return app


def run_scraper():
    """
    运行爬虫服务的主方法

    该方法创建应用上下文，初始化ScraperService，并调用process_all_charts()方法
    用于执行所有图表的数据抓取和处理
    """
    try:
        # 创建Flask应用实例
        app = create_app()

        # 使用应用上下文
        with app.app_context():
            # 初始化ScraperService
            scraper_service = ScraperService()

            # 记录开始处理的日志
            info("开始执行全图表数据抓取处理")

            # 执行全图表处理
            result = scraper_service.process_all_charts()

            # 记录处理结果
            debug(f"图表处理完成，结果：{result}")

    except Exception as e:
        # 捕获并记录任何异常
        error(f"执行抓取服务时发生错误：{str(e)}")
        raise


def main():
    """
    应用主入口函数

    根据不同的运行模式（CLI、Web服务等）执行相应的操作
    """
    # 根据需要可以添加命令行参数解析
    run_scraper()


if __name__ == '__main__':
    main()