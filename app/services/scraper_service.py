import requests
from bs4 import BeautifulSoup
import logging

from app.config.app_config import AppConfig
from app.services.actor_service import ActorService
from app.services.studio_service import StudioService


class ScraperService:
    def __init__(self,  actor_service: ActorService = None, studio_service: StudioService = None):
        config_loader = AppConfig()
        config = config_loader.get_web_scraper_config()
        self.base_url = config['javdb_url']

        self.logger = logging.getLogger(__name__)

        self.actor_service = actor_service  if actor_service is not None else ActorService()
        self.studio_service = studio_service  if studio_service is not None else StudioService()


    def scrape_movie_info(self, movie_id: str) -> dict:
        # 首先检查缓存中是否已有电影信息
        movie = self.movie_service.get(movie_id)
        if movie:
            return movie

        # 如果缓存中没有，则进行爬取
        url = f"{self.base_url}/search?q={movie_id}"
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')
        movie_info = self._extract_movie_info(soup)

        # 处理演员信息
        for actor_name in movie_info['actors']:
            actor = self.actor_service.get(actor_name)
            if not actor:
                actor = {'name': actor_name, 'movies': [movie_id]}
                self.actor_service.add(actor)
            elif movie_id not in actor['movies']:
                actor['movies'].append(movie_id)
                self.actor_service.update(actor_name, actor)

        # 处理厂商信息
        studio = self.studio_service.get(movie_info['studio'])
        if not studio:
            studio = {'name': movie_info['studio'], 'movies': [movie_id]}
            self.studio_service.add(studio)
        elif movie_id not in studio['movies']:
            studio['movies'].append(movie_id)
            self.studio_service.update(movie_info['studio'], studio)



        # 保存电影信息到缓存和数据库
        self.movie_service.add(movie_info)

        return movie_info

    def _extract_movie_info(self, soup):


        try:
            url = f"{self.base_url}/search?q={movie_id}"
            response = requests.get(url)
            soup = BeautifulSoup(response.text, 'html.parser')

            # 实现从BeautifulSoup对象中提取电影信息的逻辑
            # 这里只是一个示例，实际实现需要根据网页结构进行调整
            # 这里需要根据实际的HTML结构来提取信息
            # 以下只是示例
            javdb_id =soup.find('span', class_='movie-id').text
            title = soup.find('h3', class_='movie-title').text
            director = soup.find('span', class_='director').text
            studio = soup.find('span', class_='studio').text
            genre = [g.text for g in soup.find_all('span', class_='genre')]
            stars = [s.text for s in soup.find_all('span', class_='star')]
            actors = soup.find('span', class_='studio').text

            return {
                'title': title,
                'director': director,
                'genre': genre,
                'stars': stars
            }
        except Exception as e:
            self.logger.error(f"Error scraping info for movie {movie_id}: {str(e)}")
            return {}





    def get_magnets(self, movie_id: str):
        # 实现获取磁力链接的逻辑
        # 这里需要根据实际情况进行爬取
        pass


    def get_magnets(self, movie_id: str) -> list:
        try:
            url = f"{self.base_url}/search?q={movie_id}"
            response = requests.get(url)
            soup = BeautifulSoup(response.text, 'html.parser')

            # 这里需要根据实际的HTML结构来提取磁力链接
            # 以下只是示例
            magnets = [a['href'] for a in soup.find_all('a', class_='magnet-link')]
            return magnets
        except Exception as e:
            self.logger.error(f"Error getting magnets for movie {movie_id}: {str(e)}")
            return []