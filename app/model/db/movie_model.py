from datetime import datetime, time, date
from decimal import Decimal
from app.utils.db_util import db


class DBBaseModel(db.Model):
    __abstract__ = True

    # 公共字段
    id = db.Column(db.Integer, primary_key=True, autoincrement=True, comment='自增主键Id')
    created_at = db.Column(db.DateTime, nullable=False, server_default=db.text("CURRENT_TIMESTAMP"), comment='创建时间')
    updated_at = db.Column(db.DateTime, nullable=False,
                           server_default=db.text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"), comment='更新时间')

    def to_dict(self):
        result = {}
        for column in self.__table__.columns:
            value = getattr(self, column.name)
            if isinstance(value, datetime):
                value = value.strftime('%Y-%m-%d %H:%M:%S')
            elif isinstance(value, date):
                value = value.strftime('%Y-%m-%d')
            elif isinstance(value, time):
                value = value.strftime('%H:%M:%S')
            elif isinstance(value, Decimal):
                value = float(value)
            result[column.name] = value
        return result

    @classmethod
    def from_dict(cls, data: dict):
        if not data:
            return None
        instance = cls()
        for key, value in data.items():
            if hasattr(instance, key):
                setattr(instance, key, value)
        return instance


# 定义包含常用ID字段的混入类
class WebsiteFieldsMixin:
    javbus_id = db.Column(db.String(256, 'utf8mb4_unicode_ci'), server_default=db.text("''"), comment='javbus的id')
    javdb_id = db.Column(db.String(256, 'utf8mb4_unicode_ci'), server_default=db.text("''"), comment='javdb的id')
    javlib_id = db.Column(db.String(256, 'utf8mb4_unicode_ci'), server_default=db.text("''"), comment='javlib的id')
    avmoo_id = db.Column(db.String(256, 'utf8mb4_unicode_ci'), server_default=db.text("''"), comment='avmoo的id')
    dmm_id = db.Column(db.String(256, 'utf8mb4_unicode_ci'), server_default=db.text("''"), comment='dmm的id')


# 定义包含名称字段的混入类
class NameFieldsMixin:
    name = db.Column(db.String(256, 'utf8mb4_unicode_ci'), nullable=False, comment='名字')
    name_cn = db.Column(db.String(256, 'utf8mb4_unicode_ci'), server_default=db.text("''"), comment='中文名字')
    name_en = db.Column(db.String(256, 'utf8mb4_unicode_ci'), server_default=db.text("''"), comment='英文名字')


class Chart(DBBaseModel):
    __tablename__ = 'chart'
    __table_args__ = {'comment': '榜单表'}

    name = db.Column(db.String(256, 'utf8mb4_unicode_ci'), nullable=False, server_default=db.text("''"), comment='榜单名称')
    description = db.Column(db.String(256, 'utf8mb4_unicode_ci'), nullable=False, server_default=db.text("''"),
                            comment='榜单描述')
    chart_type_id = db.Column(db.Integer, db.ForeignKey('chart_type.id'), nullable=False, comment='榜单类型Id')

    chart_type = db.relationship("ChartType", back_populates="charts")
    entries = db.relationship("ChartEntry", back_populates="chart")
    histories = db.relationship("ChartHistory", back_populates="chart")

    # 临时属性
    file_name = ""
    file_path = ""
    movie_info_list = []
    star_info_list = []
    code_list = []
    need_state = 0


class ChartEntry(DBBaseModel):
    __tablename__ = 'chart_entry'
    __table_args__ = {'comment': '榜单条目表'}

    name = db.Column(db.String(256, 'utf8mb4_unicode_ci'), nullable=False, comment='名字')
    chart_id = db.Column(db.Integer, db.ForeignKey('chart.id'), nullable=False)
    movie_id = db.Column(db.Integer, db.ForeignKey('movie.id'), nullable=False, server_default=db.text("'0'"))
    rank = db.Column(db.Integer, nullable=False, server_default=db.text("'0'"), comment='排名')
    score = db.Column(db.Float(4), nullable=False, server_default=db.text("'0.00'"), comment='评分')
    votes = db.Column(db.Integer, nullable=False, server_default=db.text("'0'"), comment='票数')

    chart = db.relationship("Chart", back_populates="entries")
    movie = db.relationship("Movie", back_populates="chart_entries")

    # 临时属性
    tag = ""
    code = ""
    link = ""
    uri = ""
    actor_list = []
    magnet_list = []
    number_of_viewers = 0
    number_of_want_to = 0
    popularity = 0
    serial_number = ''


class ChartHistory(DBBaseModel):
    __tablename__ = 'chart_history'
    __table_args__ = {'comment': '榜单历史表'}

    chart_id = db.Column(db.Integer, db.ForeignKey('chart.id'), nullable=False)
    movie_id = db.Column(db.Integer, db.ForeignKey('movie.id'), nullable=False, server_default=db.text("'0'"))
    rank = db.Column(db.Integer, nullable=False, server_default=db.text("'0'"))
    score = db.Column(db.Float(4), nullable=False, server_default=db.text("'0.00'"))
    votes = db.Column(db.Integer, nullable=False, server_default=db.text("'0'"))
    recorded_at = db.Column(db.DateTime, nullable=False, server_default=db.text("CURRENT_TIMESTAMP"))

    chart = db.relationship("Chart", back_populates="histories")
    movie = db.relationship("Movie", back_populates="chart_histories")


class ChartType(DBBaseModel):
    __tablename__ = 'chart_type'
    __table_args__ = {'comment': '榜单类型表'}

    name = db.Column(db.String(256, 'utf8mb4_unicode_ci'), nullable=False, server_default=db.text("''"))
    description = db.Column(db.String(512, 'utf8mb4_unicode_ci'), nullable=False, server_default=db.text("''"))
    charts = db.relationship("Chart", back_populates="chart_type")


class Director(DBBaseModel, NameFieldsMixin, WebsiteFieldsMixin):
    __tablename__ = 'director'
    __table_args__ = {'comment': '导演信息表'}

    movies = db.relationship("Movie", secondary="movie_director", back_populates="directors")


class Genre(DBBaseModel, NameFieldsMixin, WebsiteFieldsMixin):
    __tablename__ = 'genre'
    __table_args__ = {'comment': '类别信息表'}

    movies = db.relationship("Movie", secondary="movie_genre", back_populates="genres")


class Label(DBBaseModel, NameFieldsMixin, WebsiteFieldsMixin):
    __tablename__ = 'label'
    __table_args__ = {'comment': '标签信息表'}

    movies = db.relationship("Movie", secondary="movie_label", back_populates="labels")


class Magnet(DBBaseModel, NameFieldsMixin, WebsiteFieldsMixin):
    __tablename__ = 'magnet'
    __table_args__ = {'comment': '磁力链接信息表'}

    magnet_xt = db.Column(db.String(64, 'utf8mb4_unicode_ci'), nullable=False, server_default=db.text("''"))
    mid = db.Column(db.String(16, 'utf8mb4_unicode_ci'), db.ForeignKey('movie.id'), nullable=False,
                    server_default=db.text("'0'"))
    censored_id = db.Column(db.String(64, 'utf8mb4_unicode_ci'), nullable=False, server_default=db.text("''"))
    type = db.Column(db.String(32, 'utf8mb4_unicode_ci'), nullable=False, server_default=db.text("''"))
    size = db.Column(db.BigInteger, nullable=False, server_default=db.text("'0'"))
    date = db.Column(db.DateTime, nullable=False, server_default=db.text("'0000-01-01 00:00:00'"))
    have_hd = db.Column(db.Integer, nullable=False, server_default=db.text("'0'"))
    have_sub = db.Column(db.Integer, nullable=False, server_default=db.text("'0'"))
    have_down = db.Column(db.Integer, nullable=False, server_default=db.text("'0'"))
    _from = db.Column('from', db.Integer, nullable=False, server_default=db.text("'0'"))
    rank = db.Column(db.Integer, nullable=False, server_default=db.text("'0'"))

    movie = db.relationship("Movie", back_populates="magnets")

class Movie(DBBaseModel,  NameFieldsMixin, WebsiteFieldsMixin):
    __tablename__ = 'movie'
    studio_id = db.Column(db.Integer, db.ForeignKey('studio.id'), nullable=False, server_default=db.text("'0'"))
    censored_id = db.Column(db.String(32, 'utf8mb4_unicode_ci'), nullable=False, server_default=db.text("''"))
    serial_number = db.Column(db.String(32, 'utf8mb4_unicode_ci'), nullable=False, server_default=db.text("''"))
    title = db.Column(db.String(512, 'utf8mb4_unicode_ci'), nullable=False, server_default=db.text("''"))
    pic_cover = db.Column(db.String(128, 'utf8mb4_unicode_ci'), nullable=False, server_default=db.text("''"))
    release_date = db.Column(db.Date, nullable=False, server_default=db.text("'1970-01-01'"))
    download_status = db.Column(db.SmallInteger, nullable=False, server_default=db.text("'0'"))
    length = db.Column(db.Integer, nullable=False, server_default=db.text("'0'"))
    similar = db.Column(db.String(128, 'utf8mb4_unicode_ci'), nullable=False, server_default=db.text("''"))
    sample_dmm = db.Column(db.Integer, nullable=False, server_default=db.text("'0'"))
    have_mg = db.Column(db.SmallInteger, nullable=False, server_default=db.text("'0'"))
    have_file = db.Column(db.SmallInteger, nullable=False, server_default=db.text("'0'"))
    have_hd = db.Column(db.SmallInteger, nullable=False, server_default=db.text("'0'"))
    have_sub = db.Column(db.SmallInteger, nullable=False, server_default=db.text("'0'"))
    have_hdbtso = db.Column(db.SmallInteger, nullable=False, server_default=db.text("'0'"))
    have_mgbtso = db.Column(db.SmallInteger, nullable=False, server_default=db.text("'0'"))
    have_file2 = db.Column(db.SmallInteger, nullable=False, server_default=db.text("'0'"))
    favorite = db.Column(db.SmallInteger, nullable=False, server_default=db.text("'0'"))
    wanted = db.Column(db.SmallInteger, nullable=False, server_default=db.text("'0'"))
    watched = db.Column(db.SmallInteger, nullable=False, server_default=db.text("'0'"))
    owned = db.Column(db.SmallInteger, nullable=False, server_default=db.text("'0'"))
    visited = db.Column(db.SmallInteger, nullable=False, server_default=db.text("'0'"))
    score = db.Column(db.Float(4), nullable=False, server_default=db.text("'0.00'"))
    userswanted = db.Column(db.Integer, nullable=False, server_default=db.text("'0'"))
    userswatched = db.Column(db.Integer, nullable=False, server_default=db.text("'0'"))
    usersowned = db.Column(db.Integer, nullable=False, server_default=db.text("'0'"))
    blogjav_img = db.Column(db.String(128, 'utf8mb4_unicode_ci'), nullable=False, server_default=db.text("''"))
    magnet_date = db.Column(db.DateTime, nullable=False, server_default=db.text("'0000-01-01 00:00:00'"))
    comments = db.Column(db.SmallInteger, nullable=False, server_default=db.text("'0'"))

    studio = db.relationship("Studio", back_populates="movies")
    directors = db.relationship("Director", secondary="movie_director", back_populates="movies")
    genres = db.relationship("Genre", secondary="movie_genre", back_populates="movies")
    labels = db.relationship("Label", secondary="movie_label", back_populates="movies")
    series = db.relationship("Series", secondary="movie_series", back_populates="movies")
    actors = db.relationship("Actor", secondary="movie_actor", back_populates="movies")
    magnets = db.relationship("Magnet", back_populates="movie")
    chart_entries = db.relationship("ChartEntry", back_populates="movie")
    chart_histories = db.relationship("ChartHistory", back_populates="movie")

def create_relation_table(name, parent_model, child_model):
    return type(name, (DBBaseModel, BaseFields), {
        '__tablename__': name.lower(),
        'movie_id': db.Column(db.Integer, db.ForeignKey(f'{parent_model.lower()}.id'), nullable=False),
        f'{child_model.lower()}_id': db.Column(db.Integer, db.ForeignKey(f'{child_model.lower()}.id'), nullable=False)
    })

MovieDirector = create_relation_table('MovieDirector', 'movie', 'director')
MovieGenre = create_relation_table('MovieGenre', 'movie', 'genre')
MovieLabel = create_relation_table('MovieLabel', 'movie', 'label')
MovieSeries = create_relation_table('MovieSeries', 'movie', 'series')
MovieActor = create_relation_table('MovieActor', 'movie', 'actor')

class Series(DBBaseModel,  NameFieldsMixin, WebsiteFieldsMixin):
    __tablename__ = 'series'
    movies = db.relationship("Movie", secondary="movie_series", back_populates="series")

class Actor(DBBaseModel,  NameFieldsMixin, WebsiteFieldsMixin):
    __tablename__ = 'actor'
    javbus_uri = db.Column(db.String(64, 'utf8mb4_unicode_ci'), nullable=False, server_default=db.text("''"))
    javdb_uri = db.Column(db.String(64, 'utf8mb4_unicode_ci'), nullable=False, server_default=db.text("''"))
    javlib_uri = db.Column(db.String(64, 'utf8mb4_unicode_ci'), nullable=False, server_default=db.text("''"))
    avmoo_uri = db.Column(db.String(64, 'utf8mb4_unicode_ci'), nullable=False, server_default=db.text("''"))
    dmm_uri = db.Column(db.String(64, 'utf8mb4_unicode_ci'), nullable=False, server_default=db.text("''"))
    birthday = db.Column(db.Date, nullable=False, server_default=db.text("'1970-01-01'"))
    age = db.Column(db.Integer, nullable=False, server_default=db.text("'0'"))
    cupsize = db.Column(db.String(8, 'utf8mb4_unicode_ci'), nullable=False, server_default=db.text("''"))
    height = db.Column(db.Integer, nullable=False, server_default=db.text("'0'"))
    bust = db.Column(db.Integer, nullable=False, server_default=db.text("'0'"))
    waist = db.Column(db.Integer, nullable=False, server_default=db.text("'0'"))
    hip = db.Column(db.Integer, nullable=False, server_default=db.text("'0'"))
    hometown = db.Column(db.String(128, 'utf8mb4_unicode_ci'), nullable=False, server_default=db.text("''"))
    hobby = db.Column(db.String(512, 'utf8mb4_unicode_ci'), nullable=False, server_default=db.text("''"))
    pic = db.Column(db.String(128, 'utf8mb4_unicode_ci'), nullable=False, server_default=db.text("''"))
    favorite = db.Column(db.SmallInteger, nullable=False, server_default=db.text("'0'"))
    movies = db.relationship("Movie", secondary="movie_actor", back_populates="actors")

class Studio(DBBaseModel,  NameFieldsMixin, WebsiteFieldsMixin):
    __tablename__ = 'studio'
    movies = db.relationship("Movie", back_populates="studio")