# app/dao/movie_dao.py
from typing import List, Optional
from sqlalchemy.orm import joinedload
from sqlalchemy import or_, desc

from app.dao.base_dao import BaseDAO
from app.model.db.movie_model import Movie, Director
from app.utils.db_util import db

class MovieDAO(BaseDAO[Movie]):
    """
    电影数据访问对象，处理与Movie模型相关的数据库操作

    继承自BaseDAO，自动实现单例模式
    """

    def __init__(self):
        """初始化MovieDAO，设置模型为Movie"""
        super().__init__(Movie)


    def get_id_by_serial_number_or_create(self, movie: Movie):
        try:
            flg = self.get_by_serial_number(movie.serial_number)
            if flg is None:
                return self.create(movie)
            else:
                return flg
        except Exception as e:
            # 处理异常
            print(f"An error occurred: {e}")
            return None
    def get_by_serial_number(self, serial_number: int) -> Optional[Movie]:

        with db.session_scope() as session:
            obj =  session.query(Movie).filter(Movie.serial_number == serial_number).first()
            return self._clone_object(obj, session) if obj else None
    def get_by_name(self, name: str) -> Optional[Movie]:

        with db.session_scope() as session:
            obj =  session.query(Movie).filter(Movie.name == name).first()
            return self._clone_object(obj, session) if obj else None
    def get_by_censored_id(self, censored_id: str) -> Optional[Movie]:
        """
        通过审查ID获取电影信息

        Args:
            censored_id (str): 电影的审查ID

        Returns:
            Optional[Movie]: 查询到的电影对象，如果不存在则返回None
        """
        with db.session_scope() as session:
            return session.query(Movie).filter(Movie.censored_id == censored_id).first()

    def get_with_relations(self, movie_id: int) -> Optional[Movie]:
        """
        获取包含所有关联信息的电影对象 TODO 导演在另外一个表

        Args:
            movie_id (int): 电影ID

        Returns:
            Optional[Movie]: 包含所有关联信息的电影对象，如果不存在则返回None
        """
        with db.session_scope() as session:
            return session.query(Movie).options(
                joinedload(Movie.directors),
                joinedload(Movie.genres),
                joinedload(Movie.labels),
                joinedload(Movie.series),
                joinedload(Movie.stars),
                joinedload(Movie.studio)
            ).filter(Movie.id == movie_id).first()

    def update_download_status(self, movie_id: int, status: int) -> bool:
        """
        更新电影的下载状态

        Args:
            movie_id (int): 电影ID
            status (int): 新的下载状态

        Returns:
            bool: 更新是否成功

        Raises:
            SQLAlchemyError: 当数据库操作失败时抛出
        """
        with db.session_scope() as session:
            movie = session.query(Movie).filter(Movie.id == movie_id).first()
            if movie:
                movie.have_file = status
                return True
            return False

    # ... 其他方法保持不变 ...
    def search_movies(self, keyword: str) -> List[Movie]:
        """
        搜索电影

        Args:
            keyword (str): 搜索关键词

        Returns:
            List[Movie]: 符合搜索条件的电影列表
        """
        with db.session_scope() as session:
            search = f"%{keyword}%"
            return session.query(Movie).filter(
                or_(
                    Movie.title.like(search),
                    Movie.censored_id.like(search),
                    Movie.serial_number.like(search)
                )
            ).all()

    def get_movies_by_director(self, director_id: int) -> List[Movie]:
        """
        获取指定导演的所有电影 TODO导演在另外一个表

        Args:
            director_id (int): 导演ID

        Returns:
            List[Movie]: 该导演参与的所有电影列表
        """
        with db.session_scope() as session:
            return session.query(Movie).join(Movie.directors).filter(Director.id == director_id).all()

    def get_movies_by_genre(self, genre_id: int) -> List[Movie]:
        """
        获取指定类型的所有电影

        Args:
            genre_id (int): 类型ID

        Returns:
            List[Movie]: 属于该类型的所有电影列表
        """
        with db.session_scope() as session:
            return session.query(Movie).join(Movie.genres).filter(Genre.id == genre_id).all()

    def get_latest_movies(self, limit: int = 10) -> List[Movie]:
        """
        获取最新的电影

        Args:
            limit (int): 返回的电影数量，默认为10

        Returns:
            List[Movie]: 最新电影列表
        """
        with db.session_scope() as session:
            return session.query(Movie).order_by(desc(Movie.release_date)).limit(limit).all()