import re
from datetime import datetime
from typing import List, Tuple, Optional

from bs4 import BeautifulSoup

from app.model.db.movie_model import Movie, Director, Actor, Series, Genre, Studio, Magnet
from app.config.log_config import debug, info, warning, error
from app.utils.parser.base_movie_parser import BaseMovieParser, ParserError
from app.utils.parser.model.movie_search_result import MovieSearchResult
from app.utils.parser.parser_factory import ParserFactory


@ParserFactory.register('javdb')
class JavdbParser(BaseMovieParser):
    """JavDB网站解析器"""

    #------------------------------- parse_movie_details_page ----start----------------------

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
        """
        解析电影详细信息
        Args:
            soup: BeautifulSoup对象,包含页面HTML内容
        Returns:
            Movie: 解析后的电影对象
        """
        try:
            debug("开始解析电影详情")
            movie = Movie()

            # 解析标题信息
            title_elem = soup.select_one('.title.is-4')
            if title_elem:
                # 获取番号和标题
                title_parts = [text.strip() for text in title_elem.stripped_strings]
                if len(title_parts) >= 2:
                    movie.serial_number = title_parts[0]
                    movie.title = title_parts[1]
                    movie.name = title_parts[1]
                    debug(f"解析到番号:{movie.serial_number}, 标题:{movie.title}")

            # 解析面板信息
            panel_blocks = soup.select('.movie-panel-info .panel-block')
            for block in panel_blocks:
                self._parse_panel_block(block, movie)

            # 解析演员信息
            self._parse_actors(soup, movie)

            # 解析导演信息
            self._parse_directors(soup, movie)

            # 解析类别信息
            self._parse_genres(soup, movie)

            # 解析系列信息
            self._parse_series(soup, movie)

            # 解析制作商信息
            self._parse_studio(soup, movie)

            # 解析用户统计信息
            self._parse_user_stats(soup, movie)

            # 解析是否有评论信息
            self._parse_comments(soup, movie)

            # 解析磁力链接
            self._parse_magnets(soup, movie)

            info(f"电影 {movie.serial_number} 解析完成")
            return movie

        except Exception as e:
            error(f"解析电影详情出错: {str(e)}")
            raise ParserError(f"解析电影详情失败: {str(e)}")

    def _parse_panel_block(self, block: BeautifulSoup, movie: Movie):
        """解析面板块信息"""
        try:
            label = self._safe_extract_text(block.select_one('strong'))
            value = self._safe_extract_text(block.select_one('.value'))

            if '番號' in label:
                movie.serial_number = value
                movie.censored_id = value
                debug(f"解析番号: {value}")
            elif '日期' in label:
                movie.release_date = self._safe_extract_date(value)
                debug(f"解析发行日期: {value}")
            elif '時長' in label:
                movie.length = self._safe_extract_int(value)
                debug(f"解析时长: {value}")
            elif '評分' in label:
                self._parse_score(value, movie)
                debug(f"解析评分: {value}")

        except Exception as e:
            warning(f"解析面板块出错: {str(e)}")

    def _parse_score(self, value: str, movie: Movie):
        """解析评分信息"""
        try:
            score_match = re.search(r'(\d+\.?\d*)分', value)
            if score_match:
                movie.score = float(score_match.group(1))

            users_match = re.search(r'由(\d+)人評價', value)
            if users_match:
                movie.userswatched = int(users_match.group(1))
        except Exception as e:
            warning(f"解析评分出错: {str(e)}")

    def _parse_actors(self, soup: BeautifulSoup, movie: Movie):
        """解析演员信息"""
        try:
            actors_block = soup.select_one('.panel-block:contains("演員")')
            if actors_block:
                actor_links = actors_block.select('a')
                for actor_link in actor_links:
                    actor = Actor()
                    actor.name = actor_link.text.strip()
                    actor.javdb_uri = actor_link.get('href', '')
                    movie.actors.append(actor)
                    debug(f"解析演员: {actor.name}")
        except Exception as e:
            warning(f"解析演员信息出错: {str(e)}")

    def _parse_directors(self, soup: BeautifulSoup, movie: Movie):
        """解析导演信息"""
        try:
            directors_block = soup.select_one('.panel-block:contains("導演")')
            if directors_block:
                director_links = directors_block.select('a')
                for director_link in director_links:
                    director = Director()
                    director.name = director_link.text.strip()
                    movie.directors.append(director)
                    debug(f"解析导演: {director.name}")
        except Exception as e:
            warning(f"解析导演信息出错: {str(e)}")

    def _parse_genres(self, soup: BeautifulSoup, movie: Movie):
        """解析类别信息"""
        try:
            genres_block = soup.select_one('.panel-block:contains("類別")')
            if genres_block:
                genre_links = genres_block.select('a')
                for genre_link in genre_links:
                    genre = Genre()
                    genre.name = genre_link.text.strip()
                    movie.genres.append(genre)
                    debug(f"解析类别: {genre.name}")
        except Exception as e:
            warning(f"解析类别信息出错: {str(e)}")

    def _parse_series(self, soup: BeautifulSoup, movie: Movie):
        """解析系列信息"""
        try:
            series_block = soup.select_one('.panel-block:contains("系列")')
            if series_block:
                series_links = series_block.select('a')
                for series_link in series_links:
                    series = Series()
                    series.name = series_link.text.strip()
                    movie.seriess.append(series)
                    debug(f"解析系列: {series.name}")
        except Exception as e:
            warning(f"解析系列信息出错: {str(e)}")

    def _parse_studio(self, soup: BeautifulSoup, movie: Movie):
        """解析制作商信息"""
        try:
            studio_block = soup.select_one('.panel-block:contains("片商")')
            if studio_block:
                studio_link = studio_block.select_one('a')
                if studio_link:
                    studio = Studio()
                    studio.name = studio_link.text.strip()
                    movie.studio = studio
                    debug(f"解析制作商: {studio.name}")
        except Exception as e:
            warning(f"解析制作商信息出错: {str(e)}")

    def _parse_user_stats(self, soup: BeautifulSoup, movie: Movie):
        """解析用户统计信息"""
        try:
            stats = soup.select_one('.video-meta-panel .is-size-7')
            if stats:
                stats_text = self._safe_extract_text(stats)
                wanted_match = re.search(r'(\d+)人想看', stats_text)
                watched_match = re.search(r'(\d+)人看過', stats_text)
                if wanted_match:
                    movie.userswanted = int(wanted_match.group(1))
                if watched_match:
                    movie.userswatched = int(watched_match.group(1))
                debug(f"解析用户统计 - 想看:{movie.userswanted}, 看过:{movie.userswatched}")
        except Exception as e:
            warning(f"解析用户统计信息出错: {str(e)}")

    def _parse_comments(self, soup: BeautifulSoup, movie: Movie):
        """解析是否有评论信息"""
        try:
            # 通过 reviewTab 直接定位到目标内容
            review_tab = soup.find(attrs={'data-movie-tab-target': 'reviewTab'})
            if not review_tab:
                return False

            # 获取 span 文本内容
            span_text = review_tab.find('span').text.strip()

            # 查找任何数字
            numbers = re.findall(r'\d+', span_text)

            movie.comments = len(numbers) > 0
            debug(f"解析是否有评论信息 - ")
        except Exception as e:
            warning(f"解析是否有评论信息出错: {str(e)}")

    def _parse_magnets(self, soup: BeautifulSoup, movie: Movie):
        """解析磁力链接信息"""
        try:
            magnets = soup.select('.magnet-links .item')
            if magnets:
                movie.have_mg = 1
                for line_number, magnet in enumerate(magnets, start=1):
                #for magnet in magnets:
                    magnet_obj = self._parse_single_magnet(magnet)
                    magnet_obj.rank = line_number
                    if magnet_obj:
                        movie.magnets.append(magnet_obj)
                        # 更新电影的HD和字幕状态
                        if magnet_obj.have_hd:
                            movie.have_hd = 1
                        if magnet_obj.have_sub:
                            movie.have_sub = 1
                        # 更新最早的磁力日期
                        if magnet_obj.date:
                            self.update_magnet_date(movie, magnet_obj.date.strftime('%Y-%m-%d'))
                debug(f"解析到 {len(movie.magnets)} 个磁力链接")
        except Exception as e:
            warning(f"解析磁力链接信息出错: {str(e)}")

    def _parse_single_magnet(self, magnet_elem: BeautifulSoup) -> Optional[Magnet]:
        """解析单个磁力链接"""
        try:
            magnet = Magnet()

            # 解析名称和大小
            name_elem = magnet_elem.select_one('.magnet-name a')
            if name_elem:
                magnet.title = name_elem.select_one('.name').text.strip()
                size_text = name_elem.select_one('.meta').text.strip()
                size_match = re.search(r'([\d.]+)([GMK]B)', size_text)
                if size_match:
                    size_num = float(size_match.group(1))
                    size_unit = size_match.group(2)
                    # 转换为字节
                    unit_multipliers = {'GB': 1024*1024*1024, 'MB': 1024*1024, 'KB': 1024}
                    magnet.size = int(size_num * unit_multipliers.get(size_unit, 1))

            # 解析磁力链接
            magnet_link = magnet_elem.select_one('a')['href']
            magnet.name = magnet_link
            if magnet_link.startswith('magnet:?xt='):
                magnet.magnet_xt = magnet_link.split('btih:')[1].split('&')[0]

            # 检查是否高清
            if magnet_elem.select_one('.tag.is-primary'):
                magnet.have_hd = 1

            # 检查是否有字幕
            if magnet_elem.select_one('.tag.is-warning'):
                magnet.have_sub = 1

            # 解析日期
            date_elem = magnet_elem.select_one('.date .time')
            if date_elem:
                magnet.date = datetime.strptime(date_elem.text.strip(), '%Y-%m-%d')

            # 设置来源为javdb
            magnet._from = 1

            return magnet
        except Exception as e:
            warning(f"解析单个磁力链接出错: {str(e)}")
            return None

    def update_magnet_date(self, movie: Movie, date_text: str) -> bool:
        """
        更新电影磁力链接的日期
        Args:
            movie: Movie对象
            date_text: 日期文本(格式:'YYYY-MM-DD')
        Returns:
            bool: 更新是否成功
        """
        try:
            if not self.is_valid_date_format(date_text):
                warning(f"无效的日期格式: {date_text}")
                return False

            magnet_date = datetime.strptime(date_text, '%Y-%m-%d')
            if (movie.magnet_date is None or
                movie.magnet_date == datetime(1970, 1, 1) or
                (magnet_date is not None and magnet_date < movie.magnet_date)):
                movie.magnet_date = magnet_date
                debug(f"更新磁力日期为: {date_text}")
                return True

        except ValueError as e:
            error(f"日期解析错误 '{date_text}': {str(e)}")
            return False

        return True

    def is_valid_date_format(self, date_text: str) -> bool:
        """
        验证日期格式是否有效
        Args:
            date_text: 日期文本
        Returns:
            bool: 是否为有效日期格式
        """
        try:
            datetime.strptime(date_text, '%Y-%m-%d')
            return True
        except ValueError:
            return False
    #------------------------------- parse_movie_details_page ----end----------------------


    #------------------------------- Search Results ----start----------------------
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

    #------------------------------- Search Results ----end----------------------
