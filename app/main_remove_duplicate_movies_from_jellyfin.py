# main_remove_duplicate_movies_from_jellyfin.py
from app.config.log_config import info, error, debug
from app.main import create_app
from app.utils.jellyfin_util import JellyfinUtil


def is_duplicate_movie(current_movie, previous_movie):
    """
    判断两部电影是否重复

    Args:
        current_movie: 当前电影详情
        previous_movie: 上一部电影详情

    Returns:
        bool: 是否重复
    """
    if not previous_movie:
        return False

    current_id = current_movie.name.split(".")[0]
    previous_id = previous_movie.name.split(".")[0]

    is_duplicate = current_id == previous_id
    if is_duplicate:
        info(f"发现重复电影 - 当前: {current_movie.name}, 前一个: {previous_movie.name}")

    return is_duplicate


def determine_movie_to_keep(current_movie, previous_movie):
    """
    根据规则决定保留哪部电影

    Args:
        current_movie: 当前电影详情
        previous_movie: 上一部电影详情

    Returns:
        tuple: (要保留的电影, 要删除的电影)
    """
    current_path = current_movie.media_sources[0].path
    previous_path = previous_movie.media_sources[0].path

    # 规则1：优先保留250目录下的电影
    if '250' in current_path and '250' not in previous_path:
        info(f"根据规则1，保留当前电影：{current_path}")
        return current_movie, previous_movie
    elif '250' in previous_path and '250' not in current_path:
        info(f"根据规则1，保留前一个电影：{previous_path}")
        return previous_movie, current_movie

    # 规则2：文件大小相同时，优先删除CACHEDEV1_DATA目录下的文件
    if current_movie.media_sources[0].size == previous_movie.media_sources[0].size:
        if 'CACHEDEV1_DATA' in previous_path:
            return current_movie, previous_movie
        elif 'CACHEDEV1_DATA' in current_path:
            return previous_movie, current_movie

    # 规则3：保留较大的文件
    current_size = current_movie.media_sources[0].size / 1073741824  # 转换为GB
    previous_size = previous_movie.media_sources[0].size / 1073741824

    info(f"文件大小比较 - 当前: {current_size:.2f}GB, 前一个: {previous_size:.2f}GB")

    if previous_size <= current_size:
        return current_movie, previous_movie
    else:
        return previous_movie, current_movie


def process_duplicates():
    """
    处理Jellyfin中的重复电影

    Returns:
        dict: 处理结果统计
    """
    jellyfin_util = JellyfinUtil()
    movies = jellyfin_util.get_all_movie_info()

    stats = {
        "total_movies": len(movies),
        "duplicates_found": 0,
        "movies_deleted": 0
    }

    previous_movie = None
    for i, movie in enumerate(movies):
        info(f"正在处理第 {i + 1}/{len(movies)} 部电影：{movie.name}")

        current_movie = jellyfin_util.get_movie_details(movie_id=movie.id)

        if is_duplicate_movie(current_movie, previous_movie):
            stats["duplicates_found"] += 1
            keep_movie, delete_movie = determine_movie_to_keep(
                current_movie, previous_movie
            )
            info(f"保留电影：{keep_movie.name},路径：{keep_movie.media_sources[0].path}")
            info(f"删除电影：{delete_movie.name},路径：{delete_movie.media_sources[0].path}")
            # TODO: 取消注释以启用实际删除
            # result = jellyfin_util.delete_movie_by_id(movie_id=delete_movie.id)
            # if result:
            #     info(f"已从Jellyfin中移除电影：{delete_movie.name}")
            #     stats["movies_deleted"] += 1

            previous_movie = keep_movie
        else:
            previous_movie = current_movie

    info(f"重复电影处理完成，统计信息：{stats}")
    return stats


def main():
    """应用入口函数"""
    try:
        app = create_app()
        with app.app_context():
            result = process_duplicates()
            info(f"重复电影处理任务完成，结果：{result}")
    except Exception as e:
        error(f"处理重复电影时发生错误：{str(e)}")
        raise


if __name__ == '__main__':
    main()