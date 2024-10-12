import logging

from app.utils import EverythingUtils
from app.config.config_log import load_logging_config
# from configbak import
from app.utils.read_markdown_file import read_line_md_file
from app.utils.read_markdown_file import read_top250_md_file

# 加载日志配置
load_logging_config()
# 创建 logger 实例
logger = logging.getLogger('fileAndConsole')


def read_md_by_one_line(path="../data/movies_list"):
    """
    读取一行的md文件
    Args:
        path: 读取路径

    Returns:

    """

    return read_line_md_file.get_movie_info_from_md()


def read_top250md(path="../data/movies_list"):
    """
    读取一行的md文件
    Args:
        path: 读取路径

    Returns:

    """

    return read_top250_md_file.get_top_250_movie_info_from_md()


# 调用业务逻辑

# 在项目入口文件中调用
if __name__ == '__main__':
    # 先加载日志配置
    # allMd = read_md_by_one_line()
    # allMd = read_top250md()
    #result = EverythingUtils().search_movie(serial_number='DMS')
    result = EverythingUtils().have_movie(serial_number='DMS')
    #result = EverythingUtils().search_movie(serial_number='运维')
    # 然后在项目中使用日志
    logger = logging.getLogger("fileAndConsole")
    logger.debug("这是一个调试日志")
    logger.info("这是一个信息日志")
    logger.error("这是一个错误日志")
