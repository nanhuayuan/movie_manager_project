# coding: utf-8
from flask_sqlalchemy import SQLAlchemy

from app.utils.db_util import db


class Chart(db.Model):
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
    # entries = db.relationship("ChartEntry", back_populates="chart")
    # histories = db.relationship("ChartHistory", back_populates="chart")


class ChartEntry(db.Model):
    __tablename__ = 'chart_entry'
    __table_args__ = {'comment': '榜单条目表'}

    id = db.Column(db.Integer, primary_key=True, autoincrement=True, comment='自增主键Id')
    # chart_id = db.Column(db.Integer, db.ForeignKey('chart.id'), nullable=False, comment='榜单Id，关联chart')
    chart_id = db.Column(db.Integer, nullable=False, comment='榜单Id，关联chart')
    movie_id = db.Column(db.Integer, nullable=False, comment='电影Id，关联movie')
    # movie_id = db.Column(db.Integer, db.ForeignKey('movie.id'), nullable=False, comment='电影Id，关联movie')
    rank = db.Column(db.Integer, nullable=False, comment='电影在榜单中的排名')
    score = db.Column(db.Float(4), nullable=False, server_default=db.text("'0.00'"), comment='电影评分')
    votes = db.Column(db.Integer, nullable=False, server_default=db.text("'0'"), comment='电影得票数或评分人数')
    status = db.Column(db.SmallInteger, nullable=False, server_default=db.text("'0'"),
                       comment='下载状态，0=不存在，1=已爬取，2=爬取失败，3=下载中，4=下载完成，5=已在电影库，6=其他状态')
    created_at = db.Column(db.DateTime, nullable=False, server_default=db.text("CURRENT_TIMESTAMP"), comment='创建时间')
    updated_at = db.Column(db.DateTime, nullable=False,
                           server_default=db.text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
                           comment='更新时间')

    # ORM层面关联
    # chart = db.relationship("Chart", back_populates="entries")
    # movie = db.relationship("Movie", back_populates="chart_entries")


class ChartHistory(db.Model):
    __tablename__ = 'chart_history'
    __table_args__ = {'comment': '榜单历史表'}

    id = db.Column(db.Integer, primary_key=True, comment='自增主键Id')
    # chart_id = db.Column(db.Integer, db.ForeignKey('chart.id'), nullable=False, comment='榜单Id，关联chart')
    chart_id = db.Column(db.Integer, nullable=False, comment='榜单Id，关联chart')
    movie_id = db.Column(db.Integer, db.ForeignKey('movie.id'), nullable=False, comment='电影Id，关联movie')
    rank = db.Column(db.Integer, nullable=False, comment='电影历史排名')
    score = db.Column(db.Float(4), nullable=False, server_default=db.text("'0.00'"), comment='电影历史评分')
    votes = db.Column(db.Integer, nullable=False, server_default=db.text("'0'"), comment='历史得票数或评分人数')
    recorded_at = db.Column(db.DateTime, nullable=False, server_default=db.text("CURRENT_TIMESTAMP"), comment='记录时间')
    created_at = db.Column(db.DateTime, nullable=False, server_default=db.text("CURRENT_TIMESTAMP"), comment='创建时间')
    updated_at = db.Column(db.DateTime, nullable=False,
                           server_default=db.text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
                           comment='更新时间')

    # chart = db.relationship("Chart", back_populates="histories")
    movie = db.relationship("Movie", back_populates="chart_histories")


class ChartType(db.Model):
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
    # 评分
    chart_file_type = None


class Director(db.Model):
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


class Genre(db.Model):
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


class Label(db.Model):
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


class Magnet(db.Model):
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
    sort = db.Column(db.Integer, nullable=False, server_default=db.text("'0'"), comment='在来源的排序')
    created_at = db.Column(db.DateTime, nullable=False, server_default=db.text("CURRENT_TIMESTAMP"), comment='创建时间')
    updated_at = db.Column(db.DateTime, nullable=False,
                           server_default=db.text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
                           comment='更新时间')

    movie = db.relationship("Movie", back_populates="magnets")


class Movie(db.Model):
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
    stars = db.relationship("Star", secondary="movie_star", back_populates="movies")
    magnets = db.relationship("Magnet", back_populates="movie")
    # chart_entries = db.relationship("ChartEntry", back_populates="movie")
    chart_histories = db.relationship("ChartHistory", back_populates="movie")

    # 普通属性
    """
    电影信息
    """
    ranking = None
    tag = ""
    code = ""
    link = ""
    uri = ""
    star_list = []
    magnet_list = []

    # 排序

    # 看过人数
    number_of_viewers = 0
    # 想看人数
    number_of_want_to = 0
    # 热度
    popularity = 0
    # 评分
    score = 0


class MovieDirector(db.Model):
    __tablename__ = 'movie_director'
    __table_args__ = {'comment': '电影与导演的关系表'}

    id = db.Column(db.Integer, primary_key=True, autoincrement=True, comment='自增主键Id')
    movie_id = db.Column(db.Integer, db.ForeignKey('movie.id'), nullable=False, comment='电影Id')
    director_id = db.Column(db.Integer, db.ForeignKey('director.id'), nullable=False, comment='导演Id')
    created_at = db.Column(db.DateTime, nullable=False, server_default=db.text("CURRENT_TIMESTAMP"), comment='创建时间')
    updated_at = db.Column(db.DateTime, nullable=False,
                           server_default=db.text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
                           comment='更新时间')


class MovieGenre(db.Model):
    __tablename__ = 'movie_genre'
    __table_args__ = {'comment': '电影与类别的关系表'}

    id = db.Column(db.Integer, primary_key=True, autoincrement=True, comment='自增主键Id')
    movie_id = db.Column(db.Integer, db.ForeignKey('movie.id'), nullable=False, comment='电影Id')
    genre_id = db.Column(db.Integer, db.ForeignKey('genre.id'), nullable=False, comment='类别Id')
    created_at = db.Column(db.DateTime, nullable=False, server_default=db.text("CURRENT_TIMESTAMP"), comment='创建时间')
    updated_at = db.Column(db.DateTime, nullable=False,
                           server_default=db.text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
                           comment='更新时间')


class MovieLabel(db.Model):
    __tablename__ = 'movie_label'
    __table_args__ = {'comment': '电影与标签的关系表'}

    id = db.Column(db.Integer, primary_key=True, autoincrement=True, comment='自增主键Id')
    movie_id = db.Column(db.Integer, db.ForeignKey('movie.id'), nullable=False, comment='电影Id')
    label_id = db.Column(db.Integer, db.ForeignKey('label.id'), nullable=False, comment='标签Id')
    created_at = db.Column(db.DateTime, nullable=False, server_default=db.text("CURRENT_TIMESTAMP"), comment='创建时间')
    updated_at = db.Column(db.DateTime, nullable=False,
                           server_default=db.text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
                           comment='更新时间')


class MovieSery(db.Model):
    __tablename__ = 'movie_series'
    __table_args__ = {'comment': '电影与系列的关系表'}

    id = db.Column(db.Integer, primary_key=True, autoincrement=True, comment='自增主键Id')
    movie_id = db.Column(db.Integer, db.ForeignKey('movie.id'), nullable=False, comment='电影Id')
    series_id = db.Column(db.Integer, db.ForeignKey('series.id'), nullable=False, comment='系列Id')
    created_at = db.Column(db.DateTime, nullable=False, server_default=db.text("CURRENT_TIMESTAMP"), comment='创建时间')
    updated_at = db.Column(db.DateTime, nullable=False,
                           server_default=db.text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
                           comment='更新时间')


class MovieStar(db.Model):
    __tablename__ = 'movie_star'
    __table_args__ = {'comment': '电影与演员的关联表'}

    id = db.Column(db.Integer, primary_key=True, autoincrement=True, comment='自增主键Id')
    movie_id = db.Column(db.Integer, db.ForeignKey('movie.id'), nullable=False, comment='电影Id')
    star_id = db.Column(db.Integer, db.ForeignKey('star.id'), nullable=False, comment='演员Id')
    created_at = db.Column(db.DateTime, nullable=False, server_default=db.text("CURRENT_TIMESTAMP"), comment='创建时间')
    updated_at = db.Column(db.DateTime, nullable=False,
                           server_default=db.text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
                           comment='更新时间')


class Series(db.Model):
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


class Star(db.Model):
    __tablename__ = 'star'
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
    dmm_id = db.Column(db.String(64, 'utf8mb4_unicode_ci'), nullable=False, server_default=db.text("''"), comment='dmm的id')
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

    movies = db.relationship("Movie", secondary="movie_star", back_populates="stars")


class Studio(db.Model):
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
