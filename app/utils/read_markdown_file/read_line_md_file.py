import os

from app.model.db.movie_model import Movie
from app.model.md_file import md_file

#from num.bean.md_file import md_file
# 获取配置中的 fileAndConsole logger

import logging
logger = logging.getLogger('fileAndConsole')


class ReadLineMdFile:
    # 获得所有的mark文件的信息
    def get_movie_info_from_md(path="../data/movies_list"):
        """
        读取md文件，获得信息
        :param path:
        :type path:
        :return:
        :rtype:
        """

        md_list = os.listdir(path)
        allMd = []
        for md in md_list:

            if "success.md" == md:
                continue

            mdFile = md_file()
            allMd.append(mdFile)

            # star_list = []

            mdFile.file_name = md
            mdFile.file_path = path + '/' + md

            movieInfoList = []
            mdFile.movie_info_list = movieInfoList
            # 转换成movie
            #mdFile.code_list = file_readlines(mdFile.file_path)
            with open(mdFile.file_path, 'r', encoding='utf-8') as file:
                for line in file.readlines():
                    movieInfo = Movie()
                    movieInfo.serial_number = line.replace("<br>\n","")
                    movieInfoList.append(movieInfo)


            # with open(mdFile.file_path, 'r', encoding='utf-8') as file:
            # for line in file.readlines():  ##readlines(),函数把所有的行都读取进来；
            # code2 = line.rstrip()
            # if len(code2) >= 1:
            # mdFile.code_list.append(code2)

        # print(len(allMd))
        return allMd

    def fail_write_to_md(allMd):
        for mdFile in allMd:
            # 原来文件路径
            filename = mdFile.file_path

            # 0 未操作
            if mdFile.need_state == 0:
                continue
            elif mdFile.need_state == 2:
                os.remove(filename)
            else:
                new_file = filename + "1"
                # 原来文件电影信息
                with open(new_file, 'w+', encoding='utf-8') as new_f:
                    for star in mdFile.star_info_list:
                        new_f.writelines(star.star_name + "\n")

                # 重命名文件
                os.remove(filename)
                os.rename(new_file, filename)


    def fail_write_code_to_md(allMd):
        for mdFile in allMd:
            # 原来文件路径
            filename = mdFile.file_path

            # 0 未操作
            if mdFile.need_state == 0:
                continue
            elif mdFile.need_state == 2:
                os.remove(filename)
            else:
                new_file = filename + "1"
                # 原来文件电影信息
                with open(new_file, 'w+', encoding='utf-8') as new_f:
                    for code3 in mdFile.code_list:
                        new_f.writelines(code3 + "\n")

                # 重命名文件
                os.remove(filename)
                os.rename(new_file, filename)


    def file_read(filepath, encoding="utf-8"):
        fr = open(filepath, mode='r', encoding=encoding)
        content = fr.read()
        fr.close()
        return content


    def file_readlines(filepath, encoding="utf-8"):
        fr = open(filepath, mode='r', encoding=encoding)
        # 读取所有行，返回列表
        content = fr.readlines()
        fr.close()

        new_content = []
        for line in content:
            new_content.append(line.rstrip())

        return new_content


    def write_file(filepath, content, model='a'):
        fw = open(filepath, mode=model, encoding="utf-8")
        fw.write(content)
        fw.close()


if __name__ == "__main__":
    #fanhao_md_info()
    # 解析md获得信息
    mdInfo = get_movie_info_from_md("../号资源 - 副本")