import os
import re
from app.model.md_file import md_file
from app.model.db.movie_model import Movie

from app.model.db.movie_model import Movie as movie

#from num.bean.md_file import md_file
# 获取配置中的 fileAndConsole logger

import logging
logger = logging.getLogger('fileAndConsole')



class ReadTop250MdFile:
    def get_top_250_movie_info_from_md(path="../data/movies_list"):
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
            mdFile = md_file()
            allMd.append(mdFile)

            movieInfoList = []
            code_list = []

            mdFile.file_name = md
            mdFile.movie_info_list = movieInfoList
            mdFile.code_list = code_list

            filePath = path + '/' + md
            with open(filePath, 'r', encoding='utf-8') as file:
                movieInfo = Movie()

                for line in file.readlines():  ##readlines(),函数把所有的行都读取进来；

                    if line.startswith("Ranking"):
                        movieInfo.ranking = line.split(": ")[1].replace("<br>\n","")
                        movieInfo.magnet = []
                    elif line.startswith("Tag"):
                         code = line.split(": ")[1].replace("<br>\n","")
                         movieInfo.serial_number = code
                         code_list.append(code)
                    else:
                        match = re.findall('\(.+?\)', line)
                        if len(match) != 0 and match[0].startswith("(https://javdb521.com"):
                            #movieInfo.link = match[0].replace("(https://javdb521.com", "https://javdb.com").replace(")", "")
                            movieInfo.uri = match[0].replace("(https://javdb521.com", "").replace(")", "")
                            movieInfoList.append(movieInfo)
                            movieInfo = Movie()
        #logger.info(len(allMd))
        return allMd

if __name__ == "__main__":
    #fanhao_md_info()
    # 解析md获得信息
    #mdInfo = get_top_250_movie_info_from_md()