import requests
from bs4 import BeautifulSoup


class MovieScraper:
    def __init__(self):
        self.base_url = "https://www.javbus.com/"

    def scrape_movie_details(self, serial_number: str):
        url = f'{self.base_url}{serial_number}'
        response = requests.get(url)
        if response.status_code != 200:
            print(f"无法抓取 {serial_number} 的信息")
            return None

        soup = BeautifulSoup(response.content, 'html.parser')

        # 示例：抓取标题、导演、演员等信息
        title = soup.find('h3').text if soup.find('h3') else '未知标题'
        director = soup.find('a', {'href': lambda x: x and 'director' in x}).text if soup.find('a', {
            'href': lambda x: x and 'director' in x}) else '未知导演'
        genre_elements = soup.find_all('span', class_='genre')
        genres = [g.text for g in genre_elements]

        # 组装数据
        movie_details = {
            'title': title,
            'director': director,
            'genres': genres,
        }

        print(f"抓取到的电影详情: {movie_details}")
        return movie_details
