from datetime import datetime
from typing import List, Tuple
from bs4 import BeautifulSoup
import re

from app.model.db.movie_model import Movie, Director, Actor, Series, Genre, Label, Studio, Magnet
from app.utils.parser.base_movie_parser import BaseMovieParser, ParserError
from app.utils.parser.model.movie_search_result import MovieSearchResult
from app.utils.parser.parser_factory import ParserFactory
from app.utils.log_util import debug, info, warning, error, critical

@ParserFactory.register('javdb')
class JavdbParser(BaseMovieParser):
    """JavDB网站解析器"""

    def parse_movie_details_page(self, soup: BeautifulSoup) -> Movie:
        """
        解析电影详情页面
        Args:
            soup: 页面HTML内容
        Returns:
            Movie: 解析后的电影对象
        """
        try:
            return self.parse_with_retry(self._parse_movie_details, soup)
        except Exception as e:
            raise ParserError(f"Failed to parse movie details: {e}")

    def _parse_movie_details(self, soup: BeautifulSoup) -> Movie:
        movie = Movie()

        # 解析面板信息
        panel_blocks = soup.select('.movie-panel-info .panel-block')
        for block in panel_blocks:
            label = self._safe_extract_text(block.select_one('strong'))
            value = self._safe_extract_text(block.select_one('.value'))

            if '番號' in label:
                #movie.serial_number = value.split('-')[1] if '-' in value else value
                movie.serial_number = value
                #movie.javdb_id = value
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
                    # 更新电影的磁力链接日期,使用一个比较逻辑来确保保存最新的日期
                    self.update_magnet_date(movie=movie, date_text=date_text)


        # 待验证
        movies = []

        try:
            video_detail = soup.find('div', class_='video-detail')
            if not video_detail:
                warning("未找到电影详情信息，可能页面结构发生了变化。")
                return movies

            # 提取电影代码和标题
            code_element = video_detail.find('h2', class_='title')
            code = code_element.find('strong').get_text(strip=True)
            title = code_element.find('strong', class_='current-title').get_text(strip=True).replace(code, "").strip()
            debug(f"解析到的电影代码: {code}, 标题: {title}")

            # 提取其他电影详细信息
            release_date = video_detail.find('div', string='日期:').find_next('span', class_='value').get_text(strip=True)
            debug(f"电影发布日期: {release_date}")

            score_info = video_detail.find('div', string='評分:').find_next('span', class_='value').get_text(strip=True)
            score_match = re.search(r'([\d.]+)分', score_info)
            score = float(score_match.group(1)) if score_match else 0.0
            vote_count_match = re.search(r'由(\d+)人評價', score_info)
            vote_count = int(vote_count_match.group(1)) if vote_count_match else 0
            debug(f"评分: {score}, 投票数: {vote_count}")

            has_subtitles = '字幕' in video_detail.get_text()
            can_play = '播放' in video_detail.get_text()
            cover_url = video_detail.find('img', class_='video-cover')['src']

            # 提取导演信息
            directors = [
                Director(name=tag.get_text(strip=True))
                for tag in video_detail.find('div', string='導演:').find_next('span', class_='value').find_all('a')
            ]
            debug(f"导演: {[director.name for director in directors]}")

            # 提取演员信息
            actors = [
                Actor(name=tag.get_text(strip=True), gender=tag.find_next('strong').get_text(strip=True))
                for tag in video_detail.find('div', string='演員:').find_next('span', class_='value').find_all('a')
            ]
            debug(f"演员: {[actor.name for actor in actors]}")

            # 提取系列、类型和标签
            series = [Series(name=tag.get_text(strip=True)) for tag in
                      video_detail.find('div', string='系列:').find_next('span', class_='value').find_all('a')]
            genres = [Genre(name=tag.get_text(strip=True)) for tag in
                      video_detail.find('div', string='類別:').find_next('span', class_='value').find_all('a')]
            labels = [Label(name=tag.get_text(strip=True)) for tag in
                      video_detail.find('div', string='類別:').find_next('span', class_='value').find_all('a')]

            # 提取制作公司
            studio_name = video_detail.find('div', string='片商:').find_next('span', class_='value').get_text(strip=True)
            studio = Studio(name=studio_name)
            debug(f"制作公司: {studio_name}")

            # 提取磁力链接
            magnets = []
            for magnet_div in soup.find_all('div', class_='item'):
                magnet_name = magnet_div.find('span', class_='name').get_text(strip=True)
                magnet_url = magnet_div.find('a')['href']
                magnet_size = magnet_div.find('span', class_='meta').get_text(strip=True)
                magnet_date = magnet_div.find('div', class_='date').find('span', class_='time').get_text(strip=True)
                magnets.append(Magnet(url=magnet_url, name=magnet_name, size=magnet_size, date=magnet_date))
            debug(f"磁力链接数量: {len(magnets)}")
        except Exception as e:
            logger.error(f"解析电影信息时发生错误: {e}")

        return movie

    def update_magnet_date(self, movie, date_text):
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

    def is_valid_date_format(self, date_text):
        try:
            datetime.strptime(date_text, '%Y-%m-%d')
            return True
        except ValueError:
            return False

    def parse_search_results(self, soup: BeautifulSoup) -> List[MovieSearchResult]:
        """
        解析搜索结果页面
        Args:
            soup: 页面HTML内容
        Returns:
            List[MovieSearchResult]: 搜索结果列表
        """
        try:
            return self.parse_with_retry(self._parse_search_results, soup)
        except Exception as e:
            raise ParserError(f"Failed to parse search results: {e}")

    def _parse_search_results(self, soup: BeautifulSoup) -> List[MovieSearchResult]:
        results = []

        if not soup:
            return results
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
                #code, title = self._extract_code_and_title(title_div.get_text(strip=True))
                code, title = self._extract_code_and_title(title_div)

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
                    cover_url=cover_url,
                    serial_number=code
                )
                results.append(result)

            except Exception as e:
                error(f"Error parsing movie item: {e}")
                continue

        return results

    def _extract_score_and_votes(self, score_text: str) -> Tuple[float, int]:
        """
        提取评分和投票数
        Args:
            score_text: 评分文本
        Returns:
            Tuple[float, int]: (评分, 投票数)
        """
        try:
            score_match = re.search(r'([\d.]+)分', score_text)
            votes_match = re.search(r'由(\d+)人評價', score_text)

            score = float(score_match.group(1)) if score_match else 0.0
            votes = int(votes_match.group(1)) if votes_match else 0

            return score, votes
        except Exception as e:
            warning(f"Failed to extract score and votes from '{score_text}': {e}")
            return 0.0, 0

    def _extract_code_and_title(self, title_div) -> Tuple[str, str]:
        """
        从提供的HTML div中提取电影代码和标题。

        参数:
            title_div (BeautifulSoup对象): 包含标题div HTML内容的BeautifulSoup对象。

        返回:
            tuple[str, str]: 包含提取出的代码和标题的元组。如果提取失败，返回空代码和完整的标题文本。
        """
        try:
            # 验证输入是否为空
            if not title_div:
                warning("收到的title_div为空或None。")
                return "", ""

            # 从<strong>标签中提取电影代码
            code_tag = title_div.find('strong')
            if code_tag:
                code = code_tag.get_text(strip=True)
                debug(f"提取到的电影代码: {code}")
            else:
                warning("在title_div中未找到<strong>标签，电影代码提取失败。")
                code = ""

            # 提取<strong>标签之外的文本内容作为标题
            # 使用get_text获取整个div的文本，并移除提取出的代码部分
            title_text = title_div.get_text(strip=True).replace(code, "").strip()
            debug(f"提取到的电影标题: {title_text}")

            return code, title_text

        except Exception as e:
            # 捕获异常并记录错误信息
            error(f"提取电影代码和标题时出现错误: {e}")
            return "", ""