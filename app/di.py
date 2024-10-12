from app.services import MovieService

from app.dao.movie_dao import MovieDAO
from app.dao.director_dao import DirectorDAO
from app.dao.genre_dao import GenreDAO
from app.dao.actor_dao import ActorDAO
from app.dao.series_dao import SeriesDAO

from app.services.movie_service import MovieService
from app.services.director_service import DirectorService
from app.services.genre_service import GenreService
from app.services.actor_service import ActorService
from app.services.series_service import SeriesService

class DependencyContainer:
    def __init__(self):
        # 初始化 DAO 层
        self.movie_dao = MovieDAO()
        self.director_dao = DirectorDAO()
        self.genre_dao = GenreDAO()
        self.actor_dao = ActorDAO()
        self.series_dao = SeriesDAO()

        # 初始化 Service 层并注入 DAO 层
        self.movie_service = MovieService(self.movie_dao)
        self.director_service = DirectorService(self.director_dao)
        self.genre_service = GenreService(self.genre_dao)
        self.actor_service = ActorService(self.actor_dao)
        self.series_service = SeriesService(self.series_dao)

dependency_container = DependencyContainer()

# 创建一个依赖注入容器实例
dependency_container = DependencyContainer()
