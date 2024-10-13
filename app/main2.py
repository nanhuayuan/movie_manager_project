from app.config.app_config import AppConfig
from core.MovieListProcessor import MovieListProcessor
from dao.MovieRepository import MovieRepository
from services.JellyfinChecker import JellyfinChecker
from services.MovieScraper import MovieScraper
from services.TorrentFetcher import TorrentFetcher
from services.QbittorrentManager import QbittorrentManager

def main():
    config_loader = AppConfig()
    db_config = config_loader.get_database_config()
    jellyfin_config = config_loader.get_jellyfin_config()
    qbittorrent_config = config_loader.get_qbittorrent_config()

    movie_repository = MovieRepository(db_config)
    jellyfin_checker = JellyfinChecker(jellyfin_config)
    movie_scraper = MovieScraper()
    torrent_fetcher = TorrentFetcher()
    qbittorrent_manager = QbittorrentManager(qbittorrent_config)

    # 处理电影列表
    movie_processor = MovieListProcessor('movies.md')
    movies = movie_processor.parse_movie_list()

    for movie in movies:
        title, year = movie['title'], movie['year']
        # 检查是否已存在于 Jellyfin 中
        if not jellyfin_checker.movie_exists_in_jellyfin(title):
            # 不存在则抓取电影信息
            movie_info = movie_scraper.scrape_movie_info(title)
            if movie_info:
                movie_repository.save_movie(movie_info)
                # 获取磁力链接并下载
                magnet_link = torrent_fetcher.fetch_magnet_link(title)
                qbittorrent_manager.add_torrent(magnet_link)

if __name__ == "__main__":
    main()
