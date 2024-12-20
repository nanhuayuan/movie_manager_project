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
from app.config.log_config import info, error

def movie_is_duplicate(movie_details, last_movie_details):
    """
    电影是否重负的
    :param movie_details: 电影详情
    :param last_movie_details: 上一个电影详情
    :return:
    """

    if last_movie_details is None:
        return False

    this_movie_fanhao = movie_details.name.split(".")[0]
    last_movie_fanhao = last_movie_details.name.split(".")[0]

    if this_movie_fanhao == last_movie_fanhao:
        info(
            "√√√√√√√√√√√√√√√√√√√√√√√√√√√√√√√√√√√√重复了，this_movie_name：【" + last_movie_details.name + "】，last_movie_name：【" + movie_details.name)
        return True
    else:
        return False


def need_remove_movie(movie_details, last_movie_details):
    """

    :param movie_details:
    :param last_movie_details:
    :return: 留下的,删除的
    """
    info("---------------------这一个路径：【" + movie_details.media_sources[0].path+"】")
    info("---------------------上一个路径：【" + last_movie_details.media_sources[0].path+"】")

    # 规则1 获取每个的详情
    # 优先路径 不是250的很可能有广告，不要
    if ('250' in movie_details.media_sources[0].path and '250' not in last_movie_details.media_sources[0].path) :
        # 删除上一个，自己变为上一个
        info("---------------------规则1，删除上一个，路径" + last_movie_details.media_sources[0].path)
        return movie_details, last_movie_details
    elif ('250' in last_movie_details.media_sources[0].path and '250' not in movie_details.media_sources[0].path):
        # 删除自己，上一个还是上一个
        info("---------------------规则1，删除自己，路径" + movie_details.media_sources[0].path)
        return last_movie_details, movie_details


    # 规则二，大小相同，删除硬盘1
    # 都是top250的，大小相同，优先删除/share/CACHEDEV1_DATA/媒体库
    if last_movie_details.media_sources[0].size == movie_details.media_sources[0].size:
        if  'CACHEDEV1_DATA' in last_movie_details.media_sources[0].path:
            # 删除上一个，自己变为上一个
            info("---------------------规则2，删除上一个，路径" + last_movie_details.media_sources[0].path)
            return movie_details, last_movie_details
        elif 'CACHEDEV1_DATA'  in movie_details.media_sources[0].path:
            # 删除自己，上一个还是上一个
            info("---------------------规则2，删除自己，路径" + movie_details.media_sources[0].path)
            return last_movie_details, movie_details

    info("*****************************这一个大小：【" + str(
        movie_details.media_sources[0].size / 1073741824) + "】，上一个大小：【" + str(
        last_movie_details.media_sources[0].size / 1073741824) + "】，这一个保留：【" + "【√】" if
                last_movie_details.media_sources[0].size <= movie_details.media_sources[0].size else "【×】")
    #规则三，删除小的其次大小
    if last_movie_details.media_sources[0].size <= movie_details.media_sources[0].size:
        # 删除上一个，自己变为上一个
        info("---------------------规则3，删除上一个，路径" + last_movie_details.media_sources[0].path)
        return movie_details, last_movie_details
    else:
        # 删除自己，上一个还是上一个
        info("---------------------规则3，删除自己，路径" + movie_details.media_sources[0].path)
        return last_movie_details, movie_details


def process(self):
    """处理所有榜单数据"""
    jellyfin_util = JellyfinUtil()
    all_movie_info_list = jellyfin_util.get_all_movie_info()

    last_movie_details = None
    # 查找重复的电影
    for i, movie in enumerate(all_movie_info_list):
        # for item in items:
        logger.info("*****************************排名：【" + str(i) + "】，编号：【" + movie.name)

        movie_details = jellyfin_util.get_movie_details(movie_id=movie.id)

        this_movie_is_duplicate = movie_is_duplicate(movie_details, last_movie_details)

        if this_movie_is_duplicate:
            # 番号相同 删除小的 只和上一个比
            movie_details, delete_movie_details = need_remove_movie(movie_details, last_movie_details)
            # 删除 在这里控制 TODO
            # result = jellyfin_util.delete_movie_by_id(movie_id=delete_movie_details.id)
            last_movie_details = movie_details
            continue

        last_movie_details = movie_details

def run_add():



    try:
        # 创建Flask应用实例
        app = create_app('dev')

        # 使用应用上下文
        with app.app_context():

            # 执行全图表处理
            result = process()

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