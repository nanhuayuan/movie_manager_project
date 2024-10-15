# app/dao/movie_dao.py
from typing import List, Optional
from sqlalchemy.orm import joinedload
from sqlalchemy import or_, desc, func
from datetime import datetime

from app.dao.base_dao import BaseDAO
from app.model.db.movie_model import Movie, Director, Genre, Star, Label, Series, Studio

class MovieDAO(BaseDAO[Movie]):
    """
    电影数据访问对象，处理与Movie模型相关的数据库操作

    继承自BaseDAO，自动实现单例模式
    """

    def __init__(self):
        """初始化MovieDAO，设置模型为Movie"""
        super().__init__(Movie)

    def get_id_by_serial_number_or_create(self, movie: Movie) -> Optional[Movie]:
        try:
            flg = self.get_by_serial_number(movie.serial_number)
            if flg is None:
                return self.create(movie)
            else:
                return flg
        except Exception as e:
            print(f"An error occurred: {e}")
            return None

    def get_by_serial_number(self, serial_number: int) -> Optional[Movie]:
        return self.db.session.query(Movie).filter(Movie.serial_number == serial_number).first()

    def get_by_name(self, name: str) -> Optional[Movie]:
        return self.db.session.query(Movie).filter(Movie.name == name).first()

    def get_by_censored_id(self, censored_id: str) -> Optional[Movie]:
        return self.db.session.query(Movie).filter(Movie.censored_id == censored_id).first()

    def get_with_relations(self, movie_id: int) -> Optional[Movie]:
        return self.db.session.query(Movie).options(
            joinedload(Movie.directors),
            joinedload(Movie.genres),
            joinedload(Movie.labels),
            joinedload(Movie.series),
            joinedload(Movie.stars),
            joinedload(Movie.studio)
        ).filter(Movie.id == movie_id).first()

    def update_download_status(self, movie_id: int, status: int) -> bool:
        movie = self.db.session.query(Movie).filter(Movie.id == movie_id).first()
        if movie:
            movie.have_file = status
            self.db.session.commit()
            return True
        return False

    def search_movies(self, keyword: str) -> List[Movie]:
        search = f"%{keyword}%"
        return self.db.session.query(Movie).filter(
            or_(
                Movie.title.like(search),
                Movie.censored_id.like(search),
                Movie.serial_number.like(search)
            )
        ).all()

    def get_movies_by_director(self, director_id: int) -> List[Movie]:
        return self.db.session.query(Movie).join(Movie.directors).filter(Director.id == director_id).all()

    def get_movies_by_genre(self, genre_id: int) -> List[Movie]:
        return self.db.session.query(Movie).join(Movie.genres).filter(Genre.id == genre_id).all()

    def get_latest_movies(self, limit: int = 10) -> List[Movie]:
        return self.db.session.query(Movie).order_by(desc(Movie.release_date)).limit(limit).all()

    # 新增方法

    def get_movies_by_star(self, star_id: int) -> List[Movie]:
        """获取指定演员出演的所有电影"""
        return self.db.session.query(Movie).join(Movie.stars).filter(Star.id == star_id).all()

    def get_movies_by_studio(self, studio_id: int) -> List[Movie]:
        """获取指定制作公司的所有电影"""
        return self.db.session.query(Movie).filter(Movie.studio_id == studio_id).all()

    def get_movies_by_release_year(self, year: int) -> List[Movie]:
        """获取指定年份发行的所有电影"""
        return self.db.session.query(Movie).filter(func.extract('year', Movie.release_date) == year).all()

    def get_movies_by_rating_range(self, min_rating: float, max_rating: float) -> List[Movie]:
        """获取指定评分范围内的所有电影"""
        return self.db.session.query(Movie).filter(Movie.rating.between(min_rating, max_rating)).all()

    def get_top_rated_movies(self, limit: int = 10) -> List[Movie]:
        """获取评分最高的电影"""
        return self.db.session.query(Movie).order_by(desc(Movie.rating)).limit(limit).all()

    def get_movies_count(self) -> int:
        """获取电影总数"""
        return self.db.session.query(func.count(Movie.id)).scalar()

    def get_movies_by_date_range(self, start_date: datetime, end_date: datetime) -> List[Movie]:
        """获取指定日期范围内发行的电影"""
        return self.db.session.query(Movie).filter(Movie.release_date.between(start_date, end_date)).all()

    def update_movie(self, movie_id: int, **kwargs) -> Optional[Movie]:
        """更新电影信息"""
        movie = self.db.session.query(Movie).filter(Movie.id == movie_id).first()
        if movie:
            for key, value in kwargs.items():
                if hasattr(movie, key):
                    setattr(movie, key, value)
            self.db.session.commit()
            return movie
        return None

    def delete_movie(self, movie_id: int) -> bool:
        """删除电影"""
        movie = self.db.session.query(Movie).filter(Movie.id == movie_id).first()
        if movie:
            self.db.session.delete(movie)
            self.db.session.commit()
            return True
        return False