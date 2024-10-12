import requests
from bs4 import BeautifulSoup

class MovieScraper:
    def scrape_movie_info(self, title):
        search_url = f"https://www.imdb.com/find?q={title.replace(' ', '+')}&s=tt"
        response = requests.get(search_url)
        soup = BeautifulSoup(response.text, 'html.parser')

        # 示例爬取逻辑，找到第一个搜索结果
        results = soup.select(".result_text a")
        if results:
            movie_page_url = "https://www.imdb.com" + results[0]['href']
            movie_info = self.scrape_movie_details(movie_page_url)
            return movie_info
        return None

    def scrape_movie_details(self, movie_page_url):
        response = requests.get(movie_page_url)
        soup = BeautifulSoup(response.text, 'html.parser')
        # 获取详细的电影信息，例如导演、演员等
        title = soup.find('h1').text.strip()
        director = soup.find('a', {'href': '/name/nm0000233/'}).text.strip()
        return {
            "title": title,
            "director": director,
            # 其他信息
        }
