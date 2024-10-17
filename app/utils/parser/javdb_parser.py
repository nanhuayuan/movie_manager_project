from datetime import datetime, date
from typing import List, Optional, Type, Dict
from bs4 import BeautifulSoup
import re

from app.model.db.movie_model import Movie
from app.utils.parser.base_movie_parser import BaseMovieParser
from app.utils.parser.model.movie_search_result import MovieSearchResult
from app.utils.parser.parser_factory import ParserFactory


@ParserFactory.register('javdb')
class JavdbParser(BaseMovieParser):
    """JavDB网站解析器"""

    def parse_movie_details_page(self, content: str) -> Movie:
        soup = BeautifulSoup(content, 'html.parser')
        movie = Movie()

        # 解析基本信息
        title_element = soup.select_one('.video-detail .title')
        if title_element:
            movie.title = self._safe_extract_text(title_element)

        # 解析面板信息
        panel_blocks = soup.select('.movie-panel-info .panel-block')
        for block in panel_blocks:
            label = self._safe_extract_text(block.select_one('strong'))
            value = self._safe_extract_text(block.select_one('.value'))

            if '番號' in label:
                movie.serial_number = value.split('-')[1] if '-' in value else value
                movie.javdb_id = value
            elif '日期' in label:
                movie.release_date = self._safe_extract_date(value)
            elif '時長' in label:
                movie.length = self._safe_extract_int(value)
            elif '導演' in label:
                pass  # 需要额外表存储
            elif '片商' in label:
                pass  # 需要额外表存储
            elif '評分' in label:
                score_match = re.search(r'(\d+\.?\d*)分', value)
                if score_match:
                    movie.score = float(score_match.group(1))
                users_match = re.search(r'由(\d+)人評價', value)
                if users_match:
                    movie.userswatched = int(users_match.group(1))

        # 解析用户统计信息
        stats = soup.select_one('.video-meta-panel .is-size-7')
        if stats:
            stats_text = self._safe_extract_text(stats)
            wanted_match = re.search(r'(\d+)人想看', stats_text)
            watched_match = re.search(r'(\d+)人看過', stats_text)
            if wanted_match:
                movie.userswanted = int(wanted_match.group(1))
            if watched_match:
                movie.userswatched = int(watched_match.group(1))

        # 解析磁力链接信息
        magnets = soup.select('.magnet-links .item')
        if magnets:
            movie.have_mg = 1
            for magnet in magnets:
                # 检查是否有高清版本
                if magnet.select_one('.tag.is-primary'):
                    movie.have_hd = 1
                # 检查是否有字幕
                if magnet.select_one('.tag.is-warning'):
                    movie.have_sub = 1
                # 获取最早的磁力日期
                date_text = self._safe_extract_text(magnet.select_one('.date .time'))
                if date_text:
                    #更新电影的磁力链接日期,使用一个比较逻辑来确保保存最新的日期
                    self.update_magnet_date(movie=movie, date_text=date_text)

        return movie



    def update_magnet_date(self,movie, date_text):
        """
        更新电影磁力链接的日期
        Args:
            movie: Movie对象
            date_text: 日期文本(格式:'YYYY-MM-DD')
        """

        if not self.is_valid_date_format(date_text):
            return False
        try:
            # 解析日期文本
            magnet_date = datetime.strptime(date_text, '%Y-%m-%d')

            # 如果当前没有日期,或日期是默认值,或新日期更早
            if (movie.magnet_date is None or
                    movie.magnet_date == datetime(1970, 1, 1) or
                    (magnet_date is not None and magnet_date < movie.magnet_date)):
                movie.magnet_date = magnet_date

        except ValueError as e:
            # 处理日期解析错误
            print(f"Error parsing date '{date_text}': {e}")
            return False

        return True

    def is_valid_date_format(self,date_text):
        try:
            datetime.strptime(date_text, '%Y-%m-%d')
            return True
        except ValueError:
            return False

    #-------------------------parse_search_results ----start------------------------------------------
    def _extract_score_and_votes(self, score_text: str) -> tuple[float, int]:
        """Extract score and vote count from score text"""
        score_match = re.search(r'([\d.]+)分', score_text)
        votes_match = re.search(r'由(\d+)人評價', score_text)

        score = float(score_match.group(1)) if score_match else 0.0
        votes = int(votes_match.group(1)) if votes_match else 0

        return score, votes

    def _extract_code_and_title(self, title_text: str) -> tuple[str, str]:
        """Extract movie code and title from title text"""
        code_match = re.search(r'<strong>(.*?)</strong>\s*(.*)', title_text)
        if code_match:
            return code_match.group(1), code_match.group(2)
        return "", title_text

    def parse_search_results(self, html_content: str) -> List[MovieSearchResult]:
        soup = BeautifulSoup(html_content, 'html.parser')
        results = []

        # Find the movie list container - using class which is more stable
        movie_list = soup.find('div', class_='movie-list')
        if not movie_list:
            return results

        # Find all movie items
        for item in movie_list.find_all('div', class_='item'):
            try:
                movie_link = item.find('a', class_='box')
                if not movie_link:
                    continue

                # Extract basic information
                uri = movie_link.get('href', '')
                title_div = movie_link.find('div', class_='video-title')
                code, title = self._extract_code_and_title(title_div.get_text(strip=True))

                # Extract score information
                score_div = movie_link.find('div', class_='score')
                score, vote_count = self._extract_score_and_votes(score_div.get_text()) if score_div else (0.0, 0)

                # Extract date
                meta_div = movie_link.find('div', class_='meta')
                release_date = meta_div.get_text(strip=True) if meta_div else ''

                # Extract cover image URL
                cover_img = movie_link.find('img')
                cover_url = cover_img.get('src', '') if cover_img else ''

                # Check for subtitles and playability
                cover_div = movie_link.find('div', class_='cover')
                tag_span = cover_div.find('span', class_='tag-can-play') if cover_div else None
                has_subtitles = 'cnsub' in tag_span.get('class', []) if tag_span else False
                can_play = bool(tag_span)

                # Check for magnet links
                tags_div = movie_link.find('div', class_='tags')
                has_magnet = bool(tags_div and tags_div.find('span', class_=['tag', 'is-success', 'is-warning']))

                result = MovieSearchResult(
                    uri=uri,
                    code=code,
                    title=title,
                    score=score,
                    vote_count=vote_count,
                    release_date=release_date,
                    has_subtitles=has_subtitles,
                    can_play=can_play,
                    has_magnet=has_magnet,
                    cover_url=cover_url
                )
                results.append(result)

            except Exception as e:
                print(f"Error parsing movie item: {e}")
                continue

        return results
    #-------------------------parse_search_results ----end------------------------------------------