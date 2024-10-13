from dependency_injector import containers, providers
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.services.cache_service import CacheService
from app.services.chart_service import ChartService
from app.services.movie_service import MovieService
from app.services.jellyfin_service import JellyfinService
from app.services.everything_service import EverythingService
from app.services.scraper_service import ScraperService
from app.services.qbittorrent_service import QBittorrentService
from app.dao.movie_dao import MovieDAO
from app.dao.magnet_dao import MagnetDAO
from app.utils import EverythingUtils
from app.utils.jellyfin_util import JellyfinUtil
from app.utils.qbittorrent_util import QBittorrentUtil
from app.utils.redis_client import RedisUtil

class Container(containers.DeclarativeContainer):
    """
    依赖注入容器类，用于管理应用程序中所有服务和DAO的实例化和生命周期。
    这个容器使用dependency_injector库来声明式地定义依赖关系。
    """

    # 配置提供者，用于加载和提供应用程序配置
    config = providers.Configuration()

    # Database
    db_engine = providers.Singleton(create_engine, config.database.url)
    db_session_factory = providers.Singleton(sessionmaker, bind=db_engine)
    #db_session = providers.Scoped(db_session_factory)

    # 单例提供者，确保整个应用只有一个Redis客户端实例
    redis_util = providers.Singleton(RedisUtil)

    # Utils
    qbittorrent_util = providers.Singleton(QBittorrentUtil)
    jellyfin_util = providers.Singleton(JellyfinUtil)
    everything_util = providers.Singleton(EverythingUtils)

    # 工厂提供者，每次请求时创建新的DAO实例
    movie_dao = providers.Singleton(MovieDAO)
    magnet_dao = providers.Singleton(MagnetDAO)
    jellyfin_service = providers.Singleton(JellyfinService)
    everything_service = providers.Singleton(EverythingService)
    scraper_service = providers.Singleton(ScraperService)
    qbittorrent_service = providers.Singleton(QBittorrentService)
    redis_client = providers.Singleton(RedisUtil)
    cache_service = providers.Singleton(CacheService)

    # 服务提供者，每次请求时创建新的服务实例
    jellyfin_service = providers.Factory(JellyfinService, config.jellyfin)
    everything_service = providers.Factory(EverythingService)
    scraper_service = providers.Factory(ScraperService, config.scraper)
    qbittorrent_service = providers.Factory(QBittorrentService, config.qbittorrent)

    # MovieService的提供者，注入所有必要的依赖
    movie_service = providers.Factory(
        MovieService,
        movie_dao=movie_dao,
        magnet_dao=magnet_dao,
        jellyfin_service=jellyfin_service,
        everything_service=everything_service,
        scraper_service=scraper_service,
        qbittorrent_service=qbittorrent_service,
        redis_client=redis_client,

        redis_util=redis_util,
        jellyfin_util=jellyfin_util,
        everything_util=everything_util,
        qbittorrent_util=qbittorrent_util
    )

    chart_service = providers.Singleton(ChartService)
