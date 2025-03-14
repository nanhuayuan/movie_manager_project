# main_add_to_playlists.py
from app.config.log_config import info, error, debug, warning
from app.main import create_app
from app.services import ChartService, JellyfinService
from app.utils.jellyfin_util import JellyfinUtil


def process_charts():
    """
    处理所有榜单数据并添加到Jellyfin播放列表

    Returns:
        dict: 处理结果统计
    """
    jellyfin_service = JellyfinService()
    chart_service = ChartService()

    info("开始处理榜单数据")
    charts = chart_service.parse_local_chartlist()
    if not charts:
        warning("未找到可用的榜单数据")
        return {"status": "error", "message": "无可用榜单数据"}

    stats = {
        "total_charts": len(charts),
        "processed_entries": 0,
        "failed_entries": 0
    }

    for chart in charts:
        info(f"正在处理榜单: {chart.name}")
        playlist_id = jellyfin_service.get_playlist_id(chart.name)

        for entry in chart.entries:
            try:
                movie = jellyfin_service.get_one_by_serial_number(
                    serial_number=entry.serial_number
                )
                if movie:
                    jellyfin_service.add_to_playlist(playlist_id, ids = movie.id)
                    stats["processed_entries"] += 1
                    debug(f"已将电影 {entry.serial_number} 添加到播放列表 '{chart.name}'")
                else:
                    warning(f"未找到对应电影: {entry.serial_number}")
                    stats["failed_entries"] += 1

            except Exception as e:
                error(f"处理榜单条目时出错: {str(e)}")
                stats["failed_entries"] += 1

    info(f"榜单处理完成，总计处理: {stats}")
    return stats


def main():
    """应用入口函数"""
    try:
        app = create_app()
        with app.app_context():
            result = process_charts()
            info(f"榜单处理任务完成，结果：{result}")
    except Exception as e:
        error(f"榜单处理过程中发生错误：{str(e)}")
        raise


if __name__ == '__main__':
    main()