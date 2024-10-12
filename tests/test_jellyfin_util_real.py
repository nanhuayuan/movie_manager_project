# tests/test_jellyfin_client.py

import unittest
from unittest.mock import Mock, patch
from app.utils.jellyfin_util import JellyfinUtil


class TestJellyfinUtil():
    """
    测试JellyfinUtil类的功能。

    这个测试类覆盖了JellyfinUtil的主要方法，包括初始化、搜索电影、
    获取电影详情、删除电影、获取播放列表等功能。每个测试方法都模拟了
    Jellyfin API的响应，以确保JellyfinUtil正确处理各种情况。
    """




if __name__ == '__main__':
    #unittest.main()
    util = JellyfinUtil()
    #search_result= utils.search_movie(title='大明王朝')
    # 电影对比
    search_result=util.get_all_movie_info()

    for item in search_result:
        print(item)

    search_result = util.search_by_serial_number(serial_number='年会不能停')
    print(search_result)

    # 添加到播放列表

    serial_number = '年会不能停'
    playlist_name = '喜剧'

    playlist_id = util.get_playlist_id(playlist_name)

    movie_id =util.get_one_id_by_serial_number_search(serial_number)

    util.add_to_playlist(playlist_id, movie_id)
