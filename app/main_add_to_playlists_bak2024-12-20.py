import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from app.config.log_config import info, error, debug
from app.main import create_app
from app.services import ChartService
from app.services.scraper_service import ScraperService
from app.utils.db_util import init_app, get_db
from app.config.log_config import warning,info, error
from app.utils.jellyfin_util import JellyfinUtil


def process_charts(self):
    """处理所有榜单数据"""
    """

    """
    jellyfin_util = JellyfinUtil()

    chart_service = ChartService()
    info("开始处理所有榜单数据")
    if not (charts := chart_service.parse_local_chartlist()):
        warning("未找到任何榜单数据")
        return
    info(f"找到 {len(charts)} 个榜单")

    for chart in charts:
        info(f"开始处理榜单: {chart.name}")

        chart_entries = list(chart.entries)
        info(f"榜单 '{chart.name}' 共有 {len(chart_entries)} 个条目")

        playlist_id = jellyfin_util.get_playlist_id(chart.name)

        for i, entry in enumerate(chart_entries):
            try:
                debug(f"处理条目: {entry.serial_number},排行: {i}")
                if movie_id := jellyfin_util.get_one_id_by_serial_number_search(serial_number = entry.serial_number):

                    # 添加到列表
                    jellyfin_util.add_to_playlist(playlist_id, movie_id)
                    info(f"榜单条目处理成功，已将电影 {entry.serial_number} 添加到列表 '{chart.name}' 中，编号: {playlist_id}")
                else:
                    warning(f"该条目不存在电影: {entry.serial_number}")

            except Exception as e:
                error(f"处理榜单 '{chart.name}' 时出错: {str(e)}")
        info(f"榜单 '{chart.name}' 处理完成")

def run_add():



    try:
        # 创建Flask应用实例
        app = create_app('dev')

        # 使用应用上下文
        with app.app_context():

            # 执行全图表处理
            result = process_charts()

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
    run_add()


if __name__ == '__main__':
    main()