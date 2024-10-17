# app/dao/movie_dao.py
from typing import List, Optional
from sqlalchemy.orm import joinedload
from sqlalchemy import or_, desc, func
from datetime import datetime

from app.dao.base_dao import BaseDAO
from app.model.db.movie_model import Movie, Director, Genre, Actor, Label, Series, Studio
from app.utils.log_util import debug, info, warning, error, critical

class MovieDAO(BaseDAO[Movie]):
    """
    电影数据访问对象，处理与Movie模型相关的数据库操作

    继承自BaseDAO，自动实现单例模式
    """

    def __init__(self):
        """
        初始化MovieDAO，设置模型为Movie

        日志记录：
        - 记录MovieDAO的初始化
        """
        super().__init__(Movie)
        info("MovieDAO initialized")

    def get_id_by_serial_number_or_create(self, movie: Movie) -> Optional[Movie]:
        """
        根据序列号获取电影ID，如果不存在则创建新的电影

        Args:
            movie (Movie): 电影对象

        Returns:
            Optional[Movie]: 获取到的或新创建的电影对象，如果发生错误则返回None

        日志记录：
        - 记录尝试获取或创建电影的操作
        - 记录操作结果
        - 记录可能发生的错误
        """
        try:
            debug(f"Attempting to get or create movie with serial number: {movie.serial_number}")
            flg = self.get_by_serial_number(movie.serial_number)
            if flg is None:
                info(f"Creating new movie with serial number: {movie.serial_number}")
                return self.create(movie)
            else:
                info(f"Movie already exists with serial number: {movie.serial_number}")
                return flg
        except Exception as e:
            error(f"An error occurred while getting or creating movie: {e}")
            return None

    def get_by_serial_number(self, serial_number: int) -> Optional[Movie]:
        """
        根据序列号获取电影

        Args:
            serial_number (int): 电影序列号

        Returns:
            Optional[Movie]: 如果找到则返回Movie对象，否则返回None

        日志记录：
        - 记录尝试获取电影的操作
        - 记录操作结果
        """
        debug(f"Attempting to get movie by serial number: {serial_number}")
        movie = self.db.session.query(Movie).filter(Movie.serial_number == serial_number).first()
        if movie:
            info(f"Movie found with serial number: {serial_number}")
        else:
            info(f"No movie found with serial number: {serial_number}")
        return movie

    # ... [其他方法的实现，每个方法都添加类似的注释和日志记录] ...

    def delete_movie(self, movie_id: int) -> bool:
        """
        删除电影

        Args:
            movie_id (int): 要删除的电影ID

        Returns:
            bool: 删除成功返回True，否则返回False

        日志记录：
        - 记录尝试删除电影的操作
        - 记录删除操作是否成功
        """
        debug(f"Attempting to delete movie with id: {movie_id}")
        movie = self.db.session.query(Movie).filter(Movie.id == movie_id).first()
        if movie:
            try:
                self.db.session.delete(movie)
                self.db.session.commit()
                info(f"Successfully deleted movie with id: {movie_id}")
                return True
            except Exception as e:
                error(f"Error while deleting movie: {e}")
                self.db.session.rollback()
                return False
        else:
            warning(f"Movie not found with id: {movie_id}")
        return False