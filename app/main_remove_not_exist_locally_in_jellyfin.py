from app.config.log_config import info, error, debug, warning
from app.main import create_app
from app.services import EverythingService
from app.utils.jellyfin_util import JellyfinUtil
from typing import Dict, Optional

# 常量定义
MIN_MOVIE_SIZE = 100 * 1024 * 1024  # 最小电影文件大小: 100MB
DEFAULT_MEDIA_PATHS = [
    '/share/CACHEDEV2_DATA/电影/Top250番号',
    '/share/CACHEDEV1_DATA/媒体库/电影'
]


def is_valid_movie_file(movie_name: str, file_info: Dict, check_path: bool = False) -> bool:
    """
    检查文件是否是有效的电影文件

    Args:
        movie_name: Jellyfin中的电影名称
        file_info: Everything搜索返回的文件信息行
        check_path: 是否检查文件路径（可选）

    Returns:
        bool: 文件是否是有效的电影文件
    """
    # 检查文件名匹配
    if movie_name not in file_info['name']:
        return False

    # 检查文件大小
    if file_info['size'] < MIN_MOVIE_SIZE:
        debug(f"文件 {file_info['name']} 小于最小大小要求({MIN_MOVIE_SIZE / 1024 / 1024:.2f}MB)")
        return False

    # 如果需要检查路径
    if check_path:
        file_path = file_info['path']
        is_in_valid_path = any(valid_path in file_path for valid_path in DEFAULT_MEDIA_PATHS)
        if not is_in_valid_path:
            debug(f"文件 {file_info['name']} 不在有效的媒体目录中")
            return False

    return True


def process_missing_movies(check_path: bool = False) -> Dict:
    """
    检查并处理Jellyfin中不存在本地文件的电影

    Args:
        check_path: 是否检查文件路径（可选）

    Returns:
        Dict: 处理结果统计信息
    """
    everything_service = EverythingService()
    jellyfin_util = JellyfinUtil()
    movies = jellyfin_util.get_all_movie_info()

    stats = {
        "total_movies": len(movies),
        "missing_files": 0,
        "deleted_entries": 0,
        "errors": 0
    }

    info(f"开始检查缺失电影文件，总计 {stats['total_movies']} 部电影")
    if check_path:
        info(f"将检查以下媒体目录: {', '.join(DEFAULT_MEDIA_PATHS)}")

    for i, movie in enumerate(movies):
        try:
            debug(f"正在检查第 {i + 1}/{stats['total_movies']} 部电影：{movie.name}")

            search_result = everything_service.search_movie(serial_number=movie.name)
            movie_exists = False

            if not search_result.empty:
                for _, row in search_result.iterrows():
                    if is_valid_movie_file(movie.name, row, check_path):
                        movie_exists = True
                        debug(f"找到有效的电影文件: {row['name']}")
                        if check_path:
                            debug(f"文件路径: {row['path']}")
                        debug(f"文件大小: {row['size'] / 1024 / 1024:.2f}MB")
                        break

            if not movie_exists:
                stats["missing_files"] += 1
                info(f"电影 {movie.name} 在本地不存在或不满足要求")
                try:
                    # TODO: 取消注释以启用实际删除
                    # result = jellyfin_util.delete_movie_by_id(movie_id=movie.id)
                    # if result:
                    #     stats["deleted_entries"] += 1
                    #     info(f"已从Jellyfin中移除电影: {movie.name}")
                    pass
                except Exception as e:
                    error(f"尝试删除电影 {movie.name} 时出错: {str(e)}")
                    stats["errors"] += 1

        except Exception as e:
            error(f"处理电影 {movie.name} 时发生错误: {str(e)}")
            stats["errors"] += 1
            continue

    # 输出统计信息
    info("缺失电影检查完成，统计信息:")
    info(f"- 总计检查: {stats['total_movies']} 部电影")
    info(f"- 缺失文件: {stats['missing_files']} 部")
    info(f"- 已删除: {stats['deleted_entries']} 部")
    if stats["errors"] > 0:
        warning(f"- 处理错误: {stats['errors']} 个")

    return stats


def main():
    """应用入口函数"""
    try:
        app = create_app()
        with app.app_context():
            # 默认不检查路径
            result = process_missing_movies(check_path=False)
            debug(f"缺失电影处理任务完成，结果：{result}")
    except Exception as e:
        error(f"处理缺失电影时发生错误：{str(e)}")
        raise


if __name__ == '__main__':
    main()