from bs4 import BeautifulSoup
from typing import Optional, List, Dict
from app.config.log_config import debug, info, warning, error, critical
class PageParserUtil:
    @staticmethod
    def extract_movie_info(soup: BeautifulSoup) -> Dict[str, any]:
        """
        从BeautifulSoup对象中提取电影信息。

        Args:
            soup (BeautifulSoup): 解析后的HTML页面。

        Returns:
            Dict[str, any]: 包含电影信息的字典。
        """
        try:
            movie_info = {
                'javdb_id': PageParserUtil._extract_text(soup, 'span', {'class': 'movie-id'}),
                'title': PageParserUtil._extract_text(soup, 'h3', {'class': 'movie-title'}),
                'director': PageParserUtil._extract_text(soup, 'span', {'class': 'director'}),
                'studio': PageParserUtil._extract_text(soup, 'span', {'class': 'studio'}),
                'genre': PageParserUtil._extract_list(soup, 'span', {'class': 'genre'}),
                'stars': PageParserUtil._extract_list(soup, 'span', {'class': 'star'}),
                'magnet_links': PageParserUtil._extract_magnet_links(soup)
            }
            return movie_info
        except Exception as e:
            error(f"提取电影信息时发生错误: {str(e)}")
            return {}

    @staticmethod
    def extract_movie_page_uri(soup: BeautifulSoup) -> Optional[str]:
        """
        从搜索结果中提取电影页面URI。

        Args:
            soup (BeautifulSoup): 解析后的HTML页面。

        Returns:
            Optional[str]: 电影页面的URI，如果未找到则返回None。
        """
        try:
            movie_list = soup.find('div', class_='movie-list')
            first_movie = movie_list.find('a')
            return first_movie['href'] if first_movie else None
        except Exception as e:
            error(f"提取电影页面URI时发生错误: {str(e)}")
            return None

    @staticmethod
    def _extract_text(soup: BeautifulSoup, tag: str, attrs: Dict[str, str]) -> str:
        element = soup.find(tag, attrs)
        return element.text.strip() if element else ""

    @staticmethod
    def _extract_list(soup: BeautifulSoup, tag: str, attrs: Dict[str, str]) -> List[str]:
        elements = soup.find_all(tag, attrs)
        return [element.text.strip() for element in elements]

    @staticmethod
    def _extract_magnet_links(soup: BeautifulSoup) -> List[str]:
        magnet_content = soup.find('div', id='magnets-content')
        if not magnet_content:
            warning("未找到磁力链接")
            return []
        return [a['href'] for a in magnet_content.find_all('a') if a['href'].startswith('magnet:')]