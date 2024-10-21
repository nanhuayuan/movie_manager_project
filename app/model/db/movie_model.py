# coding: utf-8
from decimal import Decimal

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Column, Integer, String, Date, DateTime, Float, ForeignKey, BigInteger
from app.utils.db_util import db
from datetime import datetime, time, date


class DBBaseModel(db.Model):
    __abstract__ = True

    def to_dict(self):
        result = {}
        for column in self.__table__.columns:
            value = getattr(self, column.name)
            # 直接使用 datetime
            if isinstance(value, datetime):
                value = value.strftime('%Y-%m-%d %H:%M:%S')
            elif isinstance(value,  date):
                value = value.strftime('%Y-%m-%d')
            elif isinstance(value, time):  # 如果有time类型
                value = value.strftime('%H:%M:%S')
            elif isinstance(value, Decimal):  # 如果有Decimal类型
                value = float(value)
            result[column.name] = value
        return result

    @classmethod
    def from_dict(cls, data: dict):
        """从字典创建模型实例"""
        if not data:
            return None

        instance = cls()
        for key, value in data.items():
            if hasattr(instance, key):
                setattr(instance, key, value)
        return instance

class Chart(DBBaseModel):
    __tablename__ = 'chart'
    __table_args__ = {'comment': '榜单表'}

    id = db.Column(db.Integer, primary_key=True, autoincrement=True, comment='自增主键Id')
    name = db.Column(db.String(256, 'utf8mb4_unicode_ci'), nullable=False, server_default=db.text("''"), comment='榜单名称')
    description = db.Column(db.String(256, 'utf8mb4_unicode_ci'), nullable=False, server_default=db.text("''"),
                            comment='榜单描述')
    chart_type_id = db.Column(db.Integer, db.ForeignKey('chart_type.id'), nullable=False, comment='榜单类型Id，关联chart_type') # 这个是数据库层面关联
    # chart_type_id = db.Column(db.Integer, nullable=False, comment='榜单类型Id，关联chart_type')
    created_at = db.Column(db.DateTime, nullable=False, server_default=db.text("CURRENT_TIMESTAMP"), comment='榜单创建时间')
    updated_at = db.Column(db.DateTime, nullable=False,
                           server_default=db.text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
                           comment='榜单更新时间')
    # ORM层面关联
    chart_type = db.relationship("ChartType", back_populates="charts")
    entries = db.relationship("ChartEntry", back_populates="chart")
    histories = db.relationship("ChartHistory", back_populates="chart")

    file_name = ""
    file_path = ""
    movie_info_list = []
    star_info_list = []
    code_list = []

    description = ""
    # 0-未操作 1-正操作 2-操作完成
    need_state = 0


class ChartEntry(DBBaseModel):
    __tablename__ = 'chart_entry'
    __table_args__ = {'comment': '榜单条目表'}

    id = db.Column(db.Integer, primary_key=True, autoincrement=True, comment='自增主键Id')
    #name = db.Column(db.String(256, 'utf8mb4_unicode_ci'), nullable=False, server_default=db.text("''"), comment='榜单名称')
    chart_id = db.Column(db.Integer, db.ForeignKey('chart.id'), nullable=False, comment='榜单Id，关联chart')
    # chart_id = db.Column(db.Integer, nullable=False, comment='榜单Id，关联chart')
    #movie_id = db.Column(db.Integer, nullable=False, comment='电影Id，关联movie')
    movie_id = db.Column(db.Integer, db.ForeignKey('movie.id'), nullable=False, server_default=db.text("'0'"), comment='电影Id，关联movie')
    rank = db.Column(db.Integer, nullable=False, server_default=db.text("'0'"), comment='电影在榜单中的排名')
    score = db.Column(db.Float(4), nullable=False, server_default=db.text("'0.00'"), comment='电影评分')
    votes = db.Column(db.Integer, nullable=False, server_default=db.text("'0'"), comment='电影得票数或评分人数')
    created_at = db.Column(db.DateTime, nullable=False, server_default=db.text("CURRENT_TIMESTAMP"), comment='创建时间')
    updated_at = db.Column(db.DateTime, nullable=False,
                           server_default=db.text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
                           comment='更新时间')

    # ORM层面关联
    chart = db.relationship("Chart", back_populates="entries")
    movie = db.relationship("Movie", back_populates="chart_entries")

    # 普通属性
    """
    电影信息
    """
    tag = ""
    code = ""
    link = ""
    uri = ""
    actor_list = []
    magnet_list = []

    # 排序

    # 看过人数
    number_of_viewers = 0
    # 想看人数
    number_of_want_to = 0
    # 热度
    popularity = 0
    #
    serial_number = ''

class ChartHistory(DBBaseModel):
    __tablename__ = 'chart_history'
    __table_args__ = {'comment': '榜单历史表'}

    id = db.Column(db.Integer, primary_key=True, comment='自增主键Id')
    chart_id = db.Column(db.Integer, db.ForeignKey('chart.id'), nullable=False, comment='榜单Id，关联chart')
    # chart_id = db.Column(db.Integer, nullable=False, comment='榜单Id，关联chart')
    movie_id = db.Column(db.Integer, db.ForeignKey('movie.id'), nullable=False, server_default=db.text("'0'"), comment='电影Id，关联movie')
    rank = db.Column(db.Integer, nullable=False, server_default=db.text("'0'"), comment='电影历史排名')
    score = db.Column(db.Float(4), nullable=False, server_default=db.text("'0.00'"), comment='电影历史评分')
    votes = db.Column(db.Integer, nullable=False, server_default=db.text("'0'"), comment='历史得票数或评分人数')
    recorded_at = db.Column(db.DateTime, nullable=False, server_default=db.text("CURRENT_TIMESTAMP"), comment='记录时间')
    created_at = db.Column(db.DateTime, nullable=False, server_default=db.text("CURRENT_TIMESTAMP"), comment='创建时间')
    updated_at = db.Column(db.DateTime, nullable=False,
                           server_default=db.text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
                           comment='更新时间')

    chart = db.relationship("Chart", back_populates="histories")
    movie = db.relationship("Movie", back_populates="chart_histories")


class ChartType(DBBaseModel):
    __tablename__ = 'chart_type'
    __table_args__ = {'comment': '榜单类型表'}

    id = db.Column(db.Integer, primary_key=True, autoincrement=True, comment='自增主键Id')
    name = db.Column(db.String(256, 'utf8mb4_unicode_ci'), nullable=False, server_default=db.text("''"), comment='榜单类型名称')
    description = db.Column(db.String(512, 'utf8mb4_unicode_ci'), nullable=False, server_default=db.text("''"),
                            comment='榜单类型描述')
    created_at = db.Column(db.DateTime, nullable=False, server_default=db.text("CURRENT_TIMESTAMP"), comment='创建时间')
    updated_at = db.Column(db.DateTime, nullable=False,
                           server_default=db.text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
                           comment='更新时间')

    charts = db.relationship("Chart", back_populates="chart_type")


class Director(DBBaseModel):
    __tablename__ = 'director'
    __table_args__ = {'comment': '导演信息表'}

    id = db.Column(db.Integer, primary_key=True, autoincrement=True, comment='自增主键Id')
    name = db.Column(db.String(256, 'utf8mb4_unicode_ci'), nullable=False, comment='名字')
    name_cn = db.Column(db.String(256, 'utf8mb4_unicode_ci'), nullable=False, server_default=db.text("''"), comment='中文名字')
    name_en = db.Column(db.String(256, 'utf8mb4_unicode_ci'), nullable=False, server_default=db.text("''"), comment='英文名字')
    javbus_id = db.Column(db.String(256, 'utf8mb4_unicode_ci'), nullable=False, server_default=db.text("''"),
                          comment='javbus的id')
    javdb_id = db.Column(db.String(256, 'utf8mb4_unicode_ci'), nullable=False, server_default=db.text("''"),
                         comment='javdb的id')
    javlib_id = db.Column(db.String(256, 'utf8mb4_unicode_ci'), nullable=False, server_default=db.text("''"),
                          comment='javlib的id')
    avmoo_id = db.Column(db.String(256, 'utf8mb4_unicode_ci'), nullable=False, server_default=db.text("''"),
                         comment='avmoo的id')
    dmm_id = db.Column(db.String(256, 'utf8mb4_unicode_ci'), nullable=False, server_default=db.text("''"),
                       comment='dmm的id')
    created_at = db.Column(db.DateTime, nullable=False, server_default=db.text("CURRENT_TIMESTAMP"), comment='创建时间')
    updated_at = db.Column(db.DateTime, nullable=False,
                           server_default=db.text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
                           comment='更新时间')

    movies = db.relationship("Movie", secondary="movie_director", back_populates="directors")


class Genre(DBBaseModel):
    __tablename__ = 'genre'
    __table_args__ = {'comment': '类别信息表'}

    id = db.Column(db.Integer, primary_key=True, autoincrement=True, comment='自增主键Id')
    name = db.Column(db.String(256, 'utf8mb4_unicode_ci'), nullable=False, comment='名字')
    name_cn = db.Column(db.String(256, 'utf8mb4_unicode_ci'), nullable=False, server_default=db.text("''"), comment='中文名字')
    name_en = db.Column(db.String(256, 'utf8mb4_unicode_ci'), nullable=False, server_default=db.text("''"), comment='英文名字')
    javbus_id = db.Column(db.String(256, 'utf8mb4_unicode_ci'), nullable=False, server_default=db.text("''"),
                          comment='javbus的id')
    javdb_id = db.Column(db.String(256, 'utf8mb4_unicode_ci'), nullable=False, server_default=db.text("''"),
                         comment='javdb的id')
    javlib_id = db.Column(db.String(256, 'utf8mb4_unicode_ci'), nullable=False, server_default=db.text("''"),
                          comment='javdb的id')
    avmoo_id = db.Column(db.String(256, 'utf8mb4_unicode_ci'), nullable=False, server_default=db.text("''"),
                         comment='avmoo的id')
    dmm_id = db.Column(db.String(256, 'utf8mb4_unicode_ci'), nullable=False, server_default=db.text("''"),
                       comment='cmm的id')
    created_at = db.Column(db.DateTime, nullable=False, server_default=db.text("CURRENT_TIMESTAMP"), comment='创建时间')
    updated_at = db.Column(db.DateTime, nullable=False,
                           server_default=db.text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
                           comment='更新时间')

    movies = db.relationship("Movie", secondary="movie_genre", back_populates="genres")


class Label(DBBaseModel):
    __tablename__ = 'label'
    __table_args__ = {'comment': '标签信息表'}

    id = db.Column(db.Integer, primary_key=True, autoincrement=True, comment='自增主键Id')
    name = db.Column(db.String(256, 'utf8mb4_unicode_ci'), nullable=False, comment='名字')
    name_cn = db.Column(db.String(256, 'utf8mb4_unicode_ci'), nullable=False, server_default=db.text("''"), comment='中文名字')
    name_en = db.Column(db.String(256, 'utf8mb4_unicode_ci'), nullable=False, server_default=db.text("''"), comment='英文名字')
    javbus_id = db.Column(db.String(256, 'utf8mb4_unicode_ci'), nullable=False, server_default=db.text("''"),
                          comment='javbus的id')
    javdb_id = db.Column(db.String(256, 'utf8mb4_unicode_ci'), nullable=False, server_default=db.text("''"),
                         comment='javdb的id')
    javlib_id = db.Column(db.String(256, 'utf8mb4_unicode_ci'), nullable=False, server_default=db.text("''"),
                          comment='javdb的id')
    avmoo_id = db.Column(db.String(256, 'utf8mb4_unicode_ci'), nullable=False, server_default=db.text("''"),
                         comment='avmoo的id')
    dmm_id = db.Column(db.String(256, 'utf8mb4_unicode_ci'), nullable=False, server_default=db.text("''"),
                       comment='cmm的id')
    created_at = db.Column(db.DateTime, nullable=False, server_default=db.text("CURRENT_TIMESTAMP"), comment='创建时间')
    updated_at = db.Column(db.DateTime, nullable=False,
                           server_default=db.text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
                           comment='更新时间')

    movies = db.relationship("Movie", secondary="movie_label", back_populates="labels")


class Magnet(DBBaseModel):
    __tablename__ = 'magnet'
    __table_args__ = {'comment': '磁力链接信息表'}

    id = db.Column(db.Integer, primary_key=True, autoincrement=True, comment='自增主键Id')
    name = db.Column(db.String(256, 'utf8mb4_unicode_ci'), nullable=False, server_default=db.text("''"),
                     comment='磁力链接的文件名')
    name_cn = db.Column(db.String(256, 'utf8mb4_unicode_ci'), nullable=False, server_default=db.text("''"), comment='中文名字')
    name_en = db.Column(db.String(256, 'utf8mb4_unicode_ci'), nullable=False, server_default=db.text("''"), comment='英文名字')
    javbus_id = db.Column(db.String(256, 'utf8mb4_unicode_ci'), nullable=False, server_default=db.text("''"),
                          comment='javbus的id')
    javdb_id = db.Column(db.String(256, 'utf8mb4_unicode_ci'), nullable=False, server_default=db.text("''"),
                         comment='javdb的id')
    javlib_id = db.Column(db.String(256, 'utf8mb4_unicode_ci'), nullable=False, server_default=db.text("''"),
                          comment='javdb的id')
    avmoo_id = db.Column(db.String(256, 'utf8mb4_unicode_ci'), nullable=False, server_default=db.text("''"),
                         comment='avmoo的id')
    dmm_id = db.Column(db.String(256, 'utf8mb4_unicode_ci'), nullable=False, server_default=db.text("''"),
                       comment='cmm的id')
    magnet_xt = db.Column(db.String(64, 'utf8mb4_unicode_ci'), nullable=False, server_default=db.text("''"),
                          comment='磁力链接的哈希部分，magnet:?xt=urn:btih:')
    mid = db.Column(db.String(16, 'utf8mb4_unicode_ci'), db.ForeignKey('movie.id'), nullable=False,
                    server_default=db.text("'0'"),
                    comment='关联的电影ID')
    censored_id = db.Column(db.String(64, 'utf8mb4_unicode_ci'), nullable=False, server_default=db.text("''"),
                            comment='电影的识别码')
    type = db.Column(db.String(32, 'utf8mb4_unicode_ci'), nullable=False, server_default=db.text("''"),
                     comment='磁力链接的类型，实际是大小？')
    size = db.Column(db.BigInteger, nullable=False, server_default=db.text("'0'"), comment='文件实际是大小')
    date = db.Column(db.DateTime, nullable=False, server_default=db.text("'0000-01-01 00:00:00'"), comment='磁力链接的发布日期')
    have_hd = db.Column(db.Integer, nullable=False, server_default=db.text("'0'"), comment='是否有高清版本（1: 是, 0: 否）')
    have_sub = db.Column(db.Integer, nullable=False, server_default=db.text("'0'"), comment='是否有字幕（1: 是, 0: 否）')
    have_down = db.Column(db.Integer, nullable=False, server_default=db.text("'0'"), comment='是否已下载（1: 是, 0: 否）')
    _from = db.Column('from', db.Integer, nullable=False, server_default=db.text("'0'"),
                      comment='来源（0: 其他来源,1: javdb, 2: javbus,3: javlib, 4: avmoo）')
    rank = db.Column(db.Integer, nullable=False, server_default=db.text("'0'"), comment='在来源的排序')
    created_at = db.Column(db.DateTime, nullable=False, server_default=db.text("CURRENT_TIMESTAMP"), comment='创建时间')
    updated_at = db.Column(db.DateTime, nullable=False,
                           server_default=db.text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
                           comment='更新时间')

    movie = db.relationship("Movie", back_populates="magnets")


class Movie(DBBaseModel):
    __tablename__ = 'movie'
    __table_args__ = {'comment': '电影信息表'}

    id = db.Column(db.Integer, primary_key=True, autoincrement=True, comment='自增主键Id')
    name = db.Column(db.String(256, 'utf8mb4_unicode_ci'), nullable=False, server_default=db.text("''"), comment='名字')
    name_cn = db.Column(db.String(256, 'utf8mb4_unicode_ci'), nullable=False, server_default=db.text("''"), comment='中文名字')
    name_en = db.Column(db.String(256, 'utf8mb4_unicode_ci'), nullable=False, server_default=db.text("''"), comment='英文名字')
    javbus_id = db.Column(db.String(64, 'utf8mb4_unicode_ci'), nullable=False, server_default=db.text("''"),
                          comment='javbus的id')
    javdb_id = db.Column(db.String(64, 'utf8mb4_unicode_ci'), nullable=False, server_default=db.text("''"),
                         comment='javdb的id')
    javlib_id = db.Column(db.String(64, 'utf8mb4_unicode_ci'), nullable=False, server_default=db.text("''"),
                          comment='javlib的id')
    avmoo_id = db.Column(db.String(64, 'utf8mb4_unicode_ci'), nullable=False, server_default=db.text("''"),
                         comment='avmoo的id')
    dmm_id = db.Column(db.String(64, 'utf8mb4_unicode_ci'), nullable=False, server_default=db.text("''"), comment='dmm的id')
    studio_id = db.Column(db.Integer, db.ForeignKey('studio.id'), nullable=False, server_default=db.text("'0'"),
                          comment='制作商Id')
    censored_id = db.Column(db.String(32, 'utf8mb4_unicode_ci'), nullable=False, server_default=db.text("''"),
                            comment='电影识别码')
    serial_number = db.Column(db.String(32, 'utf8mb4_unicode_ci'), nullable=False, server_default=db.text("''"),
                              comment='番号')
    title = db.Column(db.String(512, 'utf8mb4_unicode_ci'), nullable=False, server_default=db.text("''"), comment='电影标题')
    pic_cover = db.Column(db.String(128, 'utf8mb4_unicode_ci'), nullable=False, server_default=db.text("''"),
                          comment='封面图片URL')
    release_date = db.Column(db.Date, nullable=False, server_default=db.text("'1970-01-01'"), comment='发行日期')
    download_status = db.Column(db.SmallInteger, nullable=False, server_default=db.text("'0'"),
                       comment='下载状态，0=未爬取，1=已爬取，2=爬取失败，3=下载失败，4=下载中，5=下载完成，6=已在电影库，7=资源不存在，8=其他状态')
    length = db.Column(db.Integer, nullable=False, server_default=db.text("'0'"), comment='电影时长（分钟）')
    similar = db.Column(db.String(128, 'utf8mb4_unicode_ci'), nullable=False, server_default=db.text("''"),
                        comment='类似影片的URL')
    sample_dmm = db.Column(db.Integer, nullable=False, server_default=db.text("'0'"), comment='DMM网站样本图片唯一编码')
    have_mg = db.Column(db.SmallInteger, nullable=False, server_default=db.text("'0'"), comment='是否有磁力链接，0=没有，1=有，2=待定')
    have_file = db.Column(db.SmallInteger, nullable=False, server_default=db.text("'0'"), comment='是否有文件下载，0=没有，1=有，2=待定')
    have_hd = db.Column(db.SmallInteger, nullable=False, server_default=db.text("'0'"), comment='是否有高清版本，0=没有，1=有，2=待定')
    have_sub = db.Column(db.SmallInteger, nullable=False, server_default=db.text("'0'"), comment='是否有字幕，0=没有，1=有，2=待定')
    have_hdbtso = db.Column(db.SmallInteger, nullable=False, server_default=db.text("'0'"), comment='是否有高清BT种子，0=没有，1=有，2=待定')
    have_mgbtso = db.Column(db.SmallInteger, nullable=False, server_default=db.text("'0'"), comment='是否有磁力BT种子，0=没有，1=有，2=待定')
    have_file2 = db.Column(db.SmallInteger, nullable=False, server_default=db.text("'0'"), comment='是否有其他文件，0=没有，1=有，2=待定')
    favorite = db.Column(db.SmallInteger, nullable=False, server_default=db.text("'0'"), comment='收藏状态，0=未收藏，1=已收藏，2=其他状态')
    wanted = db.Column(db.SmallInteger, nullable=False, server_default=db.text("'0'"), comment='想要状态，0=不想要，1=想要，2=其他状态')
    watched = db.Column(db.SmallInteger, nullable=False, server_default=db.text("'0'"), comment='观看状态，0=未观看，1=已观看，2=其他状态')
    owned = db.Column(db.SmallInteger, nullable=False, server_default=db.text("'0'"), comment='拥有状态，0=未拥有，1=已拥有，2=其他状态')
    visited = db.Column(db.SmallInteger, nullable=False, server_default=db.text("'0'"), comment='浏览状态，0=未浏览，1=已浏览，2=其他状态')
    score = db.Column(db.Float(4), nullable=False, server_default=db.text("'0.00'"), comment='电影评分')
    userswanted = db.Column(db.Integer, nullable=False, server_default=db.text("'0'"), comment='用户想看人数')
    userswatched = db.Column(db.Integer, nullable=False, server_default=db.text("'0'"), comment='用户观看人数')
    usersowned = db.Column(db.Integer, nullable=False, server_default=db.text("'0'"), comment='用户拥有人数')
    blogjav_img = db.Column(db.String(128, 'utf8mb4_unicode_ci'), nullable=False, server_default=db.text("''"),
                            comment='BlogJAV图片URL')
    magnet_date = db.Column(db.DateTime, nullable=False, server_default=db.text("'0000-01-01 00:00:00'"), comment='磁力链接发布日期')
    comments = db.Column(db.SmallInteger, nullable=False, server_default=db.text("'0'"), comment='是否有评论，0=无，1=有，2=其他状态')
    created_at = db.Column(db.DateTime, nullable=False, server_default=db.text("CURRENT_TIMESTAMP"), comment='创建时间')
    updated_at = db.Column(db.DateTime, nullable=False,
                           server_default=db.text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
                           comment='更新时间')

    studio = db.relationship("Studio", back_populates="movies")
    directors = db.relationship("Director", secondary="movie_director", back_populates="movies")
    genres = db.relationship("Genre", secondary="movie_genre", back_populates="movies")
    labels = db.relationship("Label", secondary="movie_label", back_populates="movies")
    series = db.relationship("Series", secondary="movie_series", back_populates="movies")
    actors = db.relationship("Actor", secondary="movie_actor", back_populates="movies")
    magnets = db.relationship("Magnet", back_populates="movie")
    chart_entries = db.relationship("ChartEntry", back_populates="movie")
    chart_histories = db.relationship("ChartHistory", back_populates="movie")



class MovieDirector(DBBaseModel):
    __tablename__ = 'movie_director'
    __table_args__ = {'comment': '电影与导演的关系表'}

    id = db.Column(db.Integer, primary_key=True, autoincrement=True, comment='自增主键Id')
    movie_id = db.Column(db.Integer, db.ForeignKey('movie.id'), nullable=False, comment='电影Id')
    director_id = db.Column(db.Integer, db.ForeignKey('director.id'), nullable=False, comment='导演Id')
    created_at = db.Column(db.DateTime, nullable=False, server_default=db.text("CURRENT_TIMESTAMP"), comment='创建时间')
    updated_at = db.Column(db.DateTime, nullable=False,
                           server_default=db.text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
                           comment='更新时间')


class MovieGenre(DBBaseModel):
    __tablename__ = 'movie_genre'
    __table_args__ = {'comment': '电影与类别的关系表'}

    id = db.Column(db.Integer, primary_key=True, autoincrement=True, comment='自增主键Id')
    movie_id = db.Column(db.Integer, db.ForeignKey('movie.id'), nullable=False, comment='电影Id')
    genre_id = db.Column(db.Integer, db.ForeignKey('genre.id'), nullable=False, comment='类别Id')
    created_at = db.Column(db.DateTime, nullable=False, server_default=db.text("CURRENT_TIMESTAMP"), comment='创建时间')
    updated_at = db.Column(db.DateTime, nullable=False,
                           server_default=db.text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
                           comment='更新时间')


class MovieLabel(DBBaseModel):
    __tablename__ = 'movie_label'
    __table_args__ = {'comment': '电影与标签的关系表'}

    id = db.Column(db.Integer, primary_key=True, autoincrement=True, comment='自增主键Id')
    movie_id = db.Column(db.Integer, db.ForeignKey('movie.id'), nullable=False, comment='电影Id')
    label_id = db.Column(db.Integer, db.ForeignKey('label.id'), nullable=False, comment='标签Id')
    created_at = db.Column(db.DateTime, nullable=False, server_default=db.text("CURRENT_TIMESTAMP"), comment='创建时间')
    updated_at = db.Column(db.DateTime, nullable=False,
                           server_default=db.text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
                           comment='更新时间')


class MovieSery(DBBaseModel):
    __tablename__ = 'movie_series'
    __table_args__ = {'comment': '电影与系列的关系表'}

    id = db.Column(db.Integer, primary_key=True, autoincrement=True, comment='自增主键Id')
    movie_id = db.Column(db.Integer, db.ForeignKey('movie.id'), nullable=False, comment='电影Id')
    series_id = db.Column(db.Integer, db.ForeignKey('series.id'), nullable=False, comment='系列Id')
    created_at = db.Column(db.DateTime, nullable=False, server_default=db.text("CURRENT_TIMESTAMP"), comment='创建时间')
    updated_at = db.Column(db.DateTime, nullable=False,
                           server_default=db.text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
                           comment='更新时间')


class MovieActor(DBBaseModel):
    __tablename__ = 'movie_actor'
    __table_args__ = {'comment': '电影与演员的关联表'}

    id = db.Column(db.Integer, primary_key=True, autoincrement=True, comment='自增主键Id')
    movie_id = db.Column(db.Integer, db.ForeignKey('movie.id'), nullable=False, comment='电影Id')
    actor_id = db.Column(db.Integer, db.ForeignKey('actor.id'), nullable=False, comment='演员Id')
    created_at = db.Column(db.DateTime, nullable=False, server_default=db.text("CURRENT_TIMESTAMP"), comment='创建时间')
    updated_at = db.Column(db.DateTime, nullable=False,
                           server_default=db.text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
                           comment='更新时间')


class Series(DBBaseModel):
    __tablename__ = 'series'
    __table_args__ = {'comment': '系列信息表'}

    id = db.Column(db.Integer, primary_key=True, autoincrement=True, comment='自增主键Id')
    name = db.Column(db.String(256, 'utf8mb4_unicode_ci'), nullable=False, comment='名字')
    name_cn = db.Column(db.String(256, 'utf8mb4_unicode_ci'), nullable=False, server_default=db.text("''"), comment='中文名字')
    name_en = db.Column(db.String(256, 'utf8mb4_unicode_ci'), nullable=False, server_default=db.text("''"), comment='英文名字')
    javbus_id = db.Column(db.String(256, 'utf8mb4_unicode_ci'), nullable=False, server_default=db.text("''"),
                          comment='javbus的id')
    javdb_id = db.Column(db.String(256, 'utf8mb4_unicode_ci'), nullable=False, server_default=db.text("''"),
                         comment='javdb的id')
    javlib_id = db.Column(db.String(256, 'utf8mb4_unicode_ci'), nullable=False, server_default=db.text("''"),
                          comment='javdb的id')
    avmoo_id = db.Column(db.String(256, 'utf8mb4_unicode_ci'), nullable=False, server_default=db.text("''"),
                         comment='avmoo的id')
    dmm_id = db.Column(db.String(256, 'utf8mb4_unicode_ci'), nullable=False, server_default=db.text("''"),
                       comment='cmm的id')
    created_at = db.Column(db.DateTime, nullable=False, server_default=db.text("CURRENT_TIMESTAMP"), comment='创建时间')
    updated_at = db.Column(db.DateTime, nullable=False,
                           server_default=db.text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
                           comment='更新时间')

    movies = db.relationship("Movie", secondary="movie_series", back_populates="series")


class Actor(DBBaseModel):
    __tablename__ = 'actor'
    __table_args__ = {'comment': '演员信息表'}

    id = db.Column(db.Integer, primary_key=True, autoincrement=True, comment='自增主键Id')
    name = db.Column(db.String(256, 'utf8mb4_unicode_ci'), nullable=False, server_default=db.text("''"), comment='名字')
    name_cn = db.Column(db.String(256, 'utf8mb4_unicode_ci'), nullable=False, server_default=db.text("''"), comment='中文名字')
    name_en = db.Column(db.String(256, 'utf8mb4_unicode_ci'), nullable=False, server_default=db.text("''"), comment='英文名字')
    javbus_id = db.Column(db.String(64, 'utf8mb4_unicode_ci'), nullable=False, server_default=db.text("''"),
                          comment='javbus的id')
    javdb_id = db.Column(db.String(64, 'utf8mb4_unicode_ci'), nullable=False, server_default=db.text("''"),
                         comment='javdb的id')
    javlib_id = db.Column(db.String(64, 'utf8mb4_unicode_ci'), nullable=False, server_default=db.text("''"),
                          comment='javlib的id')
    avmoo_id = db.Column(db.String(64, 'utf8mb4_unicode_ci'), nullable=False, server_default=db.text("''"),
                         comment='avmoo的id')
    dmm_id = db.Column(db.String(64, 'utf8mb4_unicode_ci'), nullable=False, server_default=db.text("''"),
                       comment='dmm的id')
    javbus_uri = db.Column(db.String(64, 'utf8mb4_unicode_ci'), nullable=False, server_default=db.text("''"),
                          comment='javbus的演员首页')
    javdb_uri = db.Column(db.String(64, 'utf8mb4_unicode_ci'), nullable=False, server_default=db.text("''"),
                         comment='javdb的演员首页')
    javlib_uri = db.Column(db.String(64, 'utf8mb4_unicode_ci'), nullable=False, server_default=db.text("''"),
                          comment='javlib的演员首页')
    avmoo_uri = db.Column(db.String(64, 'utf8mb4_unicode_ci'), nullable=False, server_default=db.text("''"),
                         comment='avmoo的演员首页')
    dmm_uri = db.Column(db.String(64, 'utf8mb4_unicode_ci'), nullable=False, server_default=db.text("''"),
                       comment='dmm的演员首页')
    birthday = db.Column(db.Date, nullable=False, server_default=db.text("'1970-01-01'"), comment='生日')
    age = db.Column(db.Integer, nullable=False, server_default=db.text("'0'"), comment='年龄')
    cupsize = db.Column(db.String(8, 'utf8mb4_unicode_ci'), nullable=False, server_default=db.text("''"), comment='罩杯尺寸')
    height = db.Column(db.Integer, nullable=False, server_default=db.text("'0'"), comment='身高（厘米）')
    bust = db.Column(db.Integer, nullable=False, server_default=db.text("'0'"), comment='胸围（厘米）')
    waist = db.Column(db.Integer, nullable=False, server_default=db.text("'0'"), comment='腰围（厘米）')
    hip = db.Column(db.Integer, nullable=False, server_default=db.text("'0'"), comment='臀围（厘米）')
    hometown = db.Column(db.String(128, 'utf8mb4_unicode_ci'), nullable=False, server_default=db.text("''"), comment='出生地')
    hobby = db.Column(db.String(512, 'utf8mb4_unicode_ci'), nullable=False, server_default=db.text("''"), comment='兴趣爱好')
    pic = db.Column(db.String(128, 'utf8mb4_unicode_ci'), nullable=False, server_default=db.text("''"), comment='图片URL')
    favorite = db.Column(db.SmallInteger, nullable=False, server_default=db.text("'0'"), comment='收藏状态，0=未收藏，1=已收藏，2=其他状态')
    created_at = db.Column(db.DateTime, nullable=False, server_default=db.text("CURRENT_TIMESTAMP"), comment='创建时间')
    updated_at = db.Column(db.DateTime, nullable=False,
                           server_default=db.text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
                           comment='更新时间')

    movies = db.relationship("Movie", secondary="movie_actor", back_populates="actors")


class Studio(DBBaseModel):
    __tablename__ = 'studio'
    __table_args__ = {'comment': '制作商信息表'}

    id = db.Column(db.Integer, primary_key=True, autoincrement=True, comment='自增主键Id')
    name = db.Column(db.String(256, 'utf8mb4_unicode_ci'), nullable=False, server_default=db.text("''"), comment='名字')
    name_cn = db.Column(db.String(256, 'utf8mb4_unicode_ci'), nullable=False, server_default=db.text("''"), comment='中文名字')
    name_en = db.Column(db.String(256, 'utf8mb4_unicode_ci'), nullable=False, server_default=db.text("''"), comment='英文名字')
    javbus_id = db.Column(db.String(256, 'utf8mb4_unicode_ci'), nullable=False, server_default=db.text("''"),
                          comment='javbus的id')
    javdb_id = db.Column(db.String(256, 'utf8mb4_unicode_ci'), nullable=False, server_default=db.text("''"),
                         comment='javdb的id')
    javlib_id = db.Column(db.String(256, 'utf8mb4_unicode_ci'), nullable=False, server_default=db.text("''"),
                          comment='javdb的id')
    avmoo_id = db.Column(db.String(256, 'utf8mb4_unicode_ci'), nullable=False, server_default=db.text("''"),
                         comment='avmoo的id')
    dmm_id = db.Column(db.String(256, 'utf8mb4_unicode_ci'), nullable=False, server_default=db.text("''"),
                       comment='cmm的id')
    created_at = db.Column(db.DateTime, nullable=False, server_default=db.text("CURRENT_TIMESTAMP"), comment='创建时间')
    updated_at = db.Column(db.DateTime, nullable=False,
                           server_default=db.text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
                           comment='更新时间')
    movies = db.relationship("Movie", back_populates="studio")





"""

# 多对多关系表
movie_director = db.Table('movie_director',
    db.Column('id', Integer, primary_key=True, autoincrement=True),
    db.Column('movie_id', Integer, ForeignKey('movie.id')),
    db.Column('director_id', Integer, ForeignKey('director.id'))
)

movie_genre = db.Table('movie_genre',
    db.Column('id', Integer, primary_key=True, autoincrement=True),
    db.Column('movie_id', Integer, ForeignKey('movie.id')),
    db.Column('genre_id', Integer, ForeignKey('genre.id'))
)

movie_label = db.Table('movie_label',
    db.Column('id', Integer, primary_key=True, autoincrement=True),
    db.Column('movie_id', Integer, ForeignKey('movie.id')),
    db.Column('label_id', Integer, ForeignKey('label.id'))
)

movie_series = db.Table('movie_series',
    db.Column('id', Integer, primary_key=True, autoincrement=True),
     db.Column('movie_id', Integer, ForeignKey('movie.id')),
     db.Column('series_id', Integer, ForeignKey('series.id'))
)


movie_actor = db.Table('movie_actor',
    db.Column('id', Integer, primary_key=True, autoincrement=True),
    db.Column('movie_id', Integer, ForeignKey('movie.id')),
    db.Column('actor_id', Integer, ForeignKey('actor.id'))
)
"""
