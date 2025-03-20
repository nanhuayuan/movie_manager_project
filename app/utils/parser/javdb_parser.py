import re
from datetime import datetime
from typing import List, Tuple, Optional
from typing import Dict, List, Optional, Any
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

                    if not movie.serial_number:
                        raise ParserError(f"无法解析番号: {movie.serial_number}")

                    movie.title = title_parts[-1]
                    movie.name = title_parts[-1]
                    if not movie.name:
                        raise ParserError(f"无法解析番号: {movie.name}")

                    debug(f"解析到番号:{movie.serial_number}, 标题:{movie.title}, 名称:{movie.name}")

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

            if not movie.serial_number:
                warning(f"无法解析番号: {movie.serial_number}")

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
                    if actor.name and "官方" in actor.name:
                        warning(f"解析演员信息出错: {actor.name}")
                        raise ParserError(f"解析演员信息出错: {actor.name}")
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

                    if genre.name and "官方" in genre.name:
                        warning(f"解析类别信息出错: {genre.name}")
                        raise ParserError(f"解析类别信息出错: {genre.name}")

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

                    if studio.name and "官方" in studio.name:
                        warning(f"解析制作商信息出错: {studio.name}")
                        raise ParserError(f"解析制作商信息出错: {studio.name}")

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

    #------------------------------- Search actor ----start----------------------
    def parse_actor_search_results(self, soup: BeautifulSoup):
        """
        解析演员搜索结果页面
        返回演员列表，每个演员包含名称、URI和照片链接
        """
        results = []
        try:
            actors_div = soup.find('div', id='actors')

            if not actors_div:
                warning("未找到演员搜索结果区域")
                return results

            # 找到所有的actor-box
            actor_boxes = actors_div.find_all('div', class_='actor-box')

            # 遍历每个actor-box来获取其中的<a>标签
            for box in actor_boxes:
                actor_tag = box.find('a')
                if actor_tag:
                    actor_info = {
                        'name': actor_tag.get('title', '').replace(" ", "").split(",")[0],
                        'uri': actor_tag.get('href', ''),
                        'photo': actor_tag.find('img').get('src', '') if actor_tag.find('img') else ''
                    }
                    info(
                        f"演员 : 姓名={actor_info['name']}, URI={actor_info['uri']}, 照片={actor_info['photo'] or '无'}"
                    )
                    results.append(actor_info)

            return results
        except Exception as e:
            error(f"解析演员搜索结果出错: {str(e)}")
            return results

    def parse_actor_page_info(self, soup: BeautifulSoup):
        """
        解析演员页面信息，获取电影数量和最大页数
        返回 (电影数量, 最大页数)
        """
        try:
            # 获取电影总数
            movie_count = 0
            section_meta = soup.find('span', class_='section-meta')
            if section_meta:
                # 直接从"47 部影片"中提取数字
                numbers = re.findall(r'\d+', section_meta.text)
                if numbers:
                    movie_count = int(numbers[0])

            # 计算最大页数 (每页默认40个)
            items_per_page = 40
            max_page = (movie_count + items_per_page - 1) // items_per_page  # 向上取整

            # 如果计算出的页数为0，至少设为1页
            if max_page == 0:
                max_page = 1

            return movie_count, max_page
        except Exception as e:
            error(f"解析演员页面信息失败: {str(e)}")
            return 0, 1

    def parse_actor_movies_page(self, soup: BeautifulSoup):
        """
        解析演员电影页面，返回电影列表（包含评分和评价人数）
        """
        movies = []
        try:
            # 找到电影列表容器
            movie_list = soup.find('div', class_='movie-list')
            if not movie_list:
                warning("未找到电影列表区域")
                return movies

            # 遍历每个电影项
            movie_items = movie_list.find_all('div', class_='item')
            for movie_item in movie_items:
                movie_info = self._extract_movie_info(movie_item)
                if movie_info:
                    movies.append(movie_info)

            return movies
        except Exception as e:
            error(f"解析演员电影页面失败: {str(e)}")
            return []

    def _extract_movie_info(self, movie_item):
        """
        从单个电影条目中提取电影信息（包含评分和评价人数）
        """
        try:
            # 找到电影链接元素
            movie_link = movie_item.find('a', class_='box')
            if not movie_link:
                return None

            # 获取电影代码
            code_tag = movie_link.find('strong')
            if not code_tag or code_tag.text.startswith("FC2"):
                return None

            code = code_tag.text

            # 获取评分和评价人数
            score_tag = movie_link.find('span', class_='value')
            if not score_tag:
                return None

            # 提取评分和评价人数
            score, evaluations = self._extract_score_and_evaluations(score_tag.text)

            # 获取电影信息
            return {
                'code': code,
                'title': movie_link.get('title', ''),
                'uri': movie_link.get('href', ''),
                'score': score,
                'evaluations': evaluations
            }
        except Exception as e:
            error(f"提取单个电影信息失败: {str(e)}")
            return None

    def _extract_score_and_evaluations(self, score_text):
        """
        从评分文本中提取评分和评价人数
        例如: "3.96分, 由331人評價" -> (3.96, 331)
        """
        try:
            # 提取评分和评价人数
            numbers = re.findall(r'\d+\.\d+|\d+', score_text)
            if len(numbers) >= 2:
                return float(numbers[0]), int(numbers[-1])
            elif len(numbers) == 1:
                return float(numbers[0]), 0
            return 0.0, 0
        except (ValueError, IndexError):
            return 0.0, 0
    #------------------------------- Search actor ----end----------------------

    #------------------------------- actor_detail ----start----------------------
    def parse_actor_details_page(self, page_content: str) -> Dict[str, Any]:
        """解析演员详情页面，提取演员详细信息

        需要提取的信息包括：
        - 中文名/英文名
        - 生日
        - 年龄
        - 身高
        - 三围
        - 罩杯
        - 出生地
        - 兴趣爱好
        - 照片
        - ID信息
        """
        actor_details = {}
        try:
            # 这里需要根据实际网页结构编写解析逻辑
            # 以下仅为示例代码
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(page_content, 'html.parser')

            # 提取姓名
            name_element = soup.select_one('.actor-name')
            if name_element:
                actor_details['name'] = name_element.text.strip()

            # 提取中文名/英文名
            name_cn_element = soup.select_one('.actor-name-cn')
            if name_cn_element:
                actor_details['name_cn'] = name_cn_element.text.strip()

            name_en_element = soup.select_one('.actor-name-en')
            if name_en_element:
                actor_details['name_en'] = name_en_element.text.strip()

            # 提取照片
            photo_element = soup.select_one('.actor-photo img')
            if photo_element and photo_element.has_attr('src'):
                actor_details['photo'] = photo_element['src']

            # 提取详细信息
            info_elements = soup.select('.actor-info li')
            for element in info_elements:
                text = element.text.strip()

                # 解析生日
                if '生日' in text:
                    birthday_text = text.split(':', 1)[1].strip()
                    try:
                        import datetime
                        actor_details['birthday'] = datetime.datetime.strptime(birthday_text, '%Y-%m-%d').date()
                    except:
                        pass

                # 解析年龄
                elif '年龄' in text:
                    age_text = text.split(':', 1)[1].strip()
                    try:
                        actor_details['age'] = int(age_text.split('岁')[0])
                    except:
                        pass

                # 解析身高
                elif '身高' in text:
                    height_text = text.split(':', 1)[1].strip()
                    try:
                        actor_details['height'] = int(height_text.split('cm')[0])
                    except:
                        pass

                # 解析三围
                elif '三围' in text:
                    bwh_text = text.split(':', 1)[1].strip()
                    try:
                        bwh_parts = bwh_text.split('/')
                        if len(bwh_parts) >= 3:
                            actor_details['bust'] = int(bwh_parts[0].strip())
                            actor_details['waist'] = int(bwh_parts[1].strip())
                            actor_details['hip'] = int(bwh_parts[2].strip())
                    except:
                        pass

                # 解析罩杯
                elif '罩杯' in text:
                    cup_text = text.split(':', 1)[1].strip()
                    actor_details['cupsize'] = cup_text

                # 解析出生地
                elif '出生地' in text:
                    hometown_text = text.split(':', 1)[1].strip()
                    actor_details['hometown'] = hometown_text

                # 解析兴趣爱好
                elif '兴趣爱好' in text:
                    hobby_text = text.split(':', 1)[1].strip()
                    actor_details['hobby'] = hobby_text

            # 提取ID信息
            javdb_id_element = soup.select_one('.actor-javdb-id')
            if javdb_id_element:
                actor_details['javdb_id'] = javdb_id_element.text.strip()

            return actor_details
        except Exception as e:
            error(f"解析演员详情页面失败: {str(e)}")
            return {}

    #------------------------------- actor_detail ----end----------------------
