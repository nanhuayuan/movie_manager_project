# main_add_chart_to_db.py
from app.config.log_config import info, error, debug
from app.main import create_app
from app.services.scraper_service import ScraperService


def run_scraper():
    """
    运行爬虫服务，抓取并处理所有图表数据
    """
    try:
        app = create_app('test')
        with app.app_context():
            info("开始执行图表数据抓取任务")
            scraper_service = ScraperService()
            result = scraper_service.process_all_charts()
            info(f"图表数据抓取完成，处理结果：{result}")
            return result

    except Exception as e:
        error(f"图表数据抓取过程中发生错误：{str(e)}")
        raise


def main():
    """应用入口函数"""
    run_scraper()


if __name__ == '__main__':
    main()