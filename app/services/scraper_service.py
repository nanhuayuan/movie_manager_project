import requests
from bs4 import BeautifulSoup
from app.config.app_config import AppConfig
from app.services.actor_service import ActorService
from app.services.chart_entry_service import ChartEntryService
from app.services.chart_service import ChartService
from app.services.chart_type_service import ChartTypeService
from app.services.studio_service import StudioService
from app.utils.log_util import debug, info, warning, error, critical



class ScraperService:
    def __init__(self,  chart_service: ChartService = None,actor_service: ActorService = None, studio_service: StudioService = None):
        config_loader = AppConfig()
        config = config_loader.get_web_scraper_config()
        self.base_url = config['javdb_url']

        self.actor_service = actor_service  if actor_service is not None else ActorService()
        self.studio_service = studio_service  if studio_service is not None else StudioService()
        self.chart_service = chart_service  if chart_service is not None else ChartService()

        self.chart_type_service = ChartTypeService()
        self.chart_entry_service = ChartEntryService()


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
            self.error(f"Error scraping info for movie {movie_id}: {str(e)}")
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
            self.error(f"Error getting magnets for movie {movie_id}: {str(e)}")
            return []


    def aaa(self):
        """
        读取 md 文件并将数据保存到数据库
        爬取内容
        下载
        入库
        Returns:

        """
        """读取 md 文件并将数据保存到数据库"""
        chart_type = self.chart_type_service.chart_type
        reader = self.readers.get(chart_type.chart_file_type)
        if not reader:
            error(f"不支持的榜单类型: {chart_type.chart_file_type}")
            raise ValueError(f"不支持的榜单类型: {chart_type.chart_file_type}")

        md_file_list = reader.read_files()
        info(f"Reading {len(md_file_list)} files to database")

        for md_file in md_file_list:
            chart = self.chart_service.md_file_to_chart(md_file)
            for movie in md_file.movie_info_list:
                chart_entry = self.chart_entry_service.movie_to_chart_entry(movie=movie)
                chart_entry.movie = movie
                chart.entries.append(chart_entry)

            chart.chart_type = chart_type
            flg = self.chart_service.create(chart)
            info(f"Chart created: {flg}")

        """
        success_path = os.path.join(PATH, SUCCESS_FILE)
        exclude_movie_list = read_success_file(success_path)

        all_markdown_files = read_markdown_files(PATH)
      
        try:
            for markdown_file in all_markdown_files:
            
            
                """
                info(f"Processing file: {markdown_file.file_name}")
                markdown_file.need_state = 1  # 操作中

                for star in markdown_file.star_info_list[:]:  # 使用切片创建副本以允许在循环中修改列表
                    info(f"Processing star: {star.star_name}")

                    title_list, href_list = search_star_from_javdb(star.star_name)

                    for href in href_list:
                        movie_info_list = get_eligible_movies(href, COOKIE, PAGE, SORT_TYPE, NUMBER_OF_EVALUATORS,
                                                              exclude_movie_list)
                        time.sleep(random.randint(10, 30))

                        for movie_info in movie_info_list:
                            if not movie_info['uri']:
                                warning(f"No URI for movie: {movie_info['serial_number']}")
                                continue

                            magnet_list = get_movie_magnet(movie_info['uri'])
                            if not magnet_list:
                                warning(f"No magnet links for movie: {movie_info['serial_number']}")
                                continue

                            movie_info['magnet_list'] = magnet_list
                            download_success = download_by_qbittorrent(movie_info)

                            if download_success:
                                write_success_file(success_path, f"{movie_info['serial_number']}\n")

                            info("Sleeping before next download...")
                            time.sleep(random.randint(10, 20))

                    markdown_file.star_info_list.remove(star)
                    time.sleep(random.randint(10, 30))

                markdown_file.need_state = 2  # 操作完成

        finally:
            update_markdown_files(all_markdown_files)