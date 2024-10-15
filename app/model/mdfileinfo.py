

class MdFileInfo:
    """
    文件列表
    """
    file_name = ""
    file_path = ""
    movie_info_list = []
    star_info_list = []
    code_list = []

    description = ""
    # 0-未操作 1-正操作 2-操作完成
    need_state = 0