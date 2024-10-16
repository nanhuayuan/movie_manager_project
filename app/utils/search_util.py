import urllib.parse
import re
from http_util import HttpUtil
import logging

logger = logging.getLogger(__name__)

class SearchUtil:
    def search_serial_number_from_javdb(serial_number):
        """
        根据番号从javdb搜索电影信息。

        Args:
            serial_number (str): 电影的番号。

        Returns:
            tuple: 包含标题列表和链接列表的元组。
        """
        website = f'https://javdb.com/search?q={urllib.parse.quote(serial_number)}&f=all'
        logger.info(f"Searching for serial number: {serial_number}")

        soup = HttpUtil.proxy_request(website)
        movie_list = soup.find('div', class_='movie-list')
        if not movie_list:
            logger.warning(f"No results found for serial number: {serial_number}")
            return [], []

        href_list = []
        title_list = []
        for movie in movie_list.find_all('a'):
            href = 'https://javdb.com' + movie['href']
            title = movie['title']
            href_list.append(href)
            title_list.append(title)
            logger.debug(f"Found movie: {title} at {href}")

        return title_list, href_list


    def search_star_from_javdb(star_name):
        """
        根据演员名从javdb搜索演员信息。

        Args:
            star_name (str): 演员名。

        Returns:
            tuple: 包含标题列表和链接列表的元组。
        """
        website = f'https://javdb.com/search?q={urllib.parse.quote(star_name)}&f=actor'
        logger.info(f"Searching for star: {star_name}")

        soup = HttpUtil.proxy_request(website)
        actors_div = soup.find('div', id='actors')
        if not actors_div:
            logger.warning(f"No results found for star: {star_name}")
            return [], []

        href_list = []
        title_list = []
        for actor in actors_div.find_all('a'):
            href = actor['href']
            title = actor['title']
            href_list.append(href)
            title_list.append(title)
            logger.debug(f"Found actor: {title} at {href}")

        return title_list, href_list


    def get_eligible_movies(uri, cookie='', page=1, sort_type=4, number_of_evaluators=200, exclude_movie_list=[]):
        """
        获取符合条件的电影列表。

        Args:
            uri (str): 演员页面的URI。
            cookie (str, optional): 请求的Cookie。
            page (int, optional): 页码。默认为1。
            sort_type (int, optional): 排序类型。默认为4（看过人数）。
            number_of_evaluators (int, optional): 最小评价人数。默认为200。
            exclude_movie_list (list, optional): 要排除的电影列表。

        Returns:
            list: 符合条件的电影信息列表。
        """
        movie_info_list = []
        page_max = 1

        while page <= page_max:
            url = f'https://javdb.com{uri}?page={page}&sort_type={sort_type}'
            logger.info(f"Fetching eligible movies from page {page}")

            soup = HttpUtil.proxy_request(url, cookie=cookie)

            # 更新最大页码
            pagination_links = soup.find_all('a', class_='pagination-link')
            if pagination_links:
                page_max = int(pagination_links[-1].text)

            for movie_tag in soup.find_all('div', class_='item'):
                score_stars_tag = movie_tag.find('span', class_='value')
                if not score_stars_tag:
                    continue

                score_and_stars = re.findall(r'\d+\.\d+|\d+', score_stars_tag.text)
                if len(score_and_stars) > 1 and int(score_and_stars[1]) > number_of_evaluators:
                    serial_number = movie_tag.find('strong').text
                    if serial_number.startswith("FC2") or serial_number in exclude_movie_list:
                        continue

                    movie_info = {
                        'uri': movie_tag.find('a')['href'],
                        'title': movie_tag.find('a')['title'],
                        'serial_number': serial_number
                    }
                    movie_info_list.append(movie_info)
                    logger.debug(f"Found eligible movie: {serial_number}")

            page += 1

        return movie_info_list