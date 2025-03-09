from datetime import datetime, date, time
from decimal import Decimal

from app.utils.db_util import db


class DBBaseModel(db.Model):
    __abstract__ = True
    id = db.Column(db.Integer, primary_key=True, autoincrement=True, comment='自增主键Id')
    created_at = db.Column(db.DateTime, nullable=False, server_default=db.text("CURRENT_TIMESTAMP"))
    updated_at = db.Column(db.DateTime, nullable=False,
                           server_default=db.text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"))

    def to_dict(self):
        return {c.name: self._format_value(getattr(self, c.name)) for c in self.__table__.columns}

    @staticmethod
    def _format_value(value):
        formats = {datetime: '%Y-%m-%d %H:%M:%S', date: '%Y-%m-%d', time: '%H:%M:%S'}
        return value.strftime(formats[type(value)]) if type(value) in formats else float(value) if isinstance(value,
                                                                                                              Decimal) else value

    @classmethod
    def from_dict(cls, data):
        return cls(**{k: v for k, v in (data or {}).items() if hasattr(cls, k)}) if data else None


class BaseMixin:
    _sites = ['javbus', 'javdb', 'javlib', 'avmoo', 'dmm']
    locals().update({
        f"{site}_id": db.Column(db.String(256, 'utf8mb4_unicode_ci'), server_default=db.text("''"))
        for site in _sites
    })
    name = db.Column(db.String(1024, 'utf8mb4_unicode_ci'), nullable=False)
    name_cn = db.Column(db.String(1024, 'utf8mb4_unicode_ci'), server_default=db.text("''"))
    name_en = db.Column(db.String(1024, 'utf8mb4_unicode_ci'), server_default=db.text("''"))


# 创建关系表（不包含Studio）
RELATION_MODELS = ['Director', 'Genre', 'Label', 'Series', 'Actor']
relation_tables = {
    f'movie_{name.lower()}': db.Table(
        f'movie_{name.lower()}',
        db.Column('movie_id', db.Integer, db.ForeignKey('movie.id'), primary_key=True),
        db.Column(f'{name.lower()}_id', db.Integer, db.ForeignKey(f'{name.lower()}.id'), primary_key=True)
    ) for name in RELATION_MODELS
}


class Chart(DBBaseModel):
    __tablename__ = 'chart'
    name = db.Column(db.String(256, 'utf8mb4_unicode_ci'), nullable=False, server_default=db.text("''"))
    description = db.Column(db.String(256, 'utf8mb4_unicode_ci'), nullable=False, server_default=db.text("''"))
    chart_type_id = db.Column(db.Integer, db.ForeignKey('chart_type.id'), nullable=False)
    chart_type = db.relationship("ChartType", back_populates="charts")
    entries = db.relationship("ChartEntry", back_populates="chart")
    histories = db.relationship("ChartHistory", back_populates="chart")

    # 临时属性
    file_name = ""
    file_path = ""

class ChartEntry(DBBaseModel):
    __tablename__ = 'chart_entry'
    name = db.Column(db.String(256, 'utf8mb4_unicode_ci'), nullable=False, server_default=db.text("''"))
    chart_id = db.Column(db.Integer, db.ForeignKey('chart.id'), nullable=False)
    movie_id = db.Column(db.Integer, db.ForeignKey('movie.id'), nullable=False, server_default=db.text("'0'"))
    rank = db.Column(db.Integer, nullable=False, server_default=db.text("'0'"))
    score = db.Column(db.Float(4), nullable=False, server_default=db.text("'0.00'"))
    votes = db.Column(db.Integer, nullable=False, server_default=db.text("'0'"))
    chart = db.relationship("Chart", back_populates="entries")
    movie = db.relationship("Movie", back_populates="chart_entries")

    uri = ""
    serial_number = ''
    chart_type_name = ''
    chart_type_description = ''
    chart_name = ''


class ChartHistory(DBBaseModel):
    __tablename__ = 'chart_history'
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
    name = db.Column(db.String(256, 'utf8mb4_unicode_ci'), nullable=False, server_default=db.text("''"))
    description = db.Column(db.String(512, 'utf8mb4_unicode_ci'), nullable=False, server_default=db.text("''"))
    charts = db.relationship("Chart", back_populates="chart_type")


class Movie(DBBaseModel, BaseMixin):
    __tablename__ = 'movie'
    studio_id = db.Column(db.Integer, db.ForeignKey('studio.id'), nullable=False, server_default=db.text("'0'"))
    censored_id = db.Column(db.String(32, 'utf8mb4_unicode_ci'), server_default=db.text("''"))
    serial_number = db.Column(db.String(32, 'utf8mb4_unicode_ci'), server_default=db.text("''"))
    title = db.Column(db.String(512, 'utf8mb4_unicode_ci'), server_default=db.text("''"))
    pic_cover = db.Column(db.String(128, 'utf8mb4_unicode_ci'), server_default=db.text("''"))
    release_date = db.Column(db.Date, nullable=False, server_default=db.text("'1970-01-01'"))
    length = db.Column(db.Integer, server_default=db.text("'0'"))
    similar = db.Column(db.String(128, 'utf8mb4_unicode_ci'), server_default=db.text("''"))
    blogjav_img = db.Column(db.String(128, 'utf8mb4_unicode_ci'), server_default=db.text("''"))
    magnet_date = db.Column(db.DateTime, server_default=db.text("'0000-01-01 00:00:00'"))
    score = db.Column(db.Float(4), nullable=False, server_default=db.text("'0.00'"))

    # 使用字典推导式简化布尔标志和数值字段的创建
    locals().update({
        flag: db.Column(db.SmallInteger, nullable=False, server_default=db.text("'0'"))
        for flag in ['download_status', 'sample_dmm', 'have_mg', 'have_file', 'have_hd', 'have_sub',
                     'have_hdbtso', 'have_mgbtso', 'have_file2', 'favorite', 'wanted', 'watched',
                     'owned', 'visited', 'comments']
    })
    locals().update({
        stat: db.Column(db.Integer, nullable=False, server_default=db.text("'0'"))
        for stat in ['userswanted', 'userswatched', 'usersowned']
    })

    # 关系
    studio = db.relationship("Studio", back_populates="movies")
    magnets = db.relationship("Magnet", back_populates="movie")
    chart_entries = db.relationship("ChartEntry", back_populates="movie")
    chart_histories = db.relationship("ChartHistory", back_populates="movie")

    # 动态创建many-to-many关系
    locals().update({
        f"{model.lower()}s": db.relationship(model, secondary=relation_tables[f'movie_{model.lower()}'],
                                             back_populates="movies")
        for model in RELATION_MODELS
    })


class Magnet(DBBaseModel, BaseMixin):
    __tablename__ = 'magnet'
    title = db.Column(db.String(1024, 'utf8mb4_unicode_ci'), nullable=False, server_default=db.text("''"))
    magnet_xt = db.Column(db.String(1024, 'utf8mb4_unicode_ci'), nullable=False, server_default=db.text("''"))
    mid = db.Column(db.String(16, 'utf8mb4_unicode_ci'), db.ForeignKey('movie.id'), nullable=False,
                    server_default=db.text("'0'"))
    censored_id = db.Column(db.String(64, 'utf8mb4_unicode_ci'), server_default=db.text("''"))
    type = db.Column(db.String(32, 'utf8mb4_unicode_ci'), server_default=db.text("''"))
    size = db.Column(db.BigInteger, server_default=db.text("'0'"))
    date = db.Column(db.DateTime, server_default=db.text("'0000-01-01 00:00:00'"))
    _from = db.Column('from', db.Integer, server_default=db.text("'0'"))
    rank = db.Column(db.Integer, server_default=db.text("'0'"))
    locals().update({
        flag: db.Column(db.Integer, nullable=False, server_default=db.text("'0'"))
        for flag in ['have_hd', 'have_sub', 'have_down']
    })
    movie = db.relationship("Movie", back_populates="magnets")


# 为Director, Genre, Label, Series创建模型
for model_name in RELATION_MODELS[:-1]:  # 不包含Actor，因为它有特殊字段
    globals()[model_name] = type(model_name, (DBBaseModel, BaseMixin), {
        '__tablename__': model_name.lower(),
        'movies': db.relationship("Movie", secondary=relation_tables[f'movie_{model_name.lower()}'],
                                  back_populates=f"{model_name.lower()}s")
    })


# Studio模型（不使用关系表）
class Studio(DBBaseModel, BaseMixin):
    __tablename__ = 'studio'
    movies = db.relationship("Movie", back_populates="studio")


class Actor(DBBaseModel, BaseMixin):
    __tablename__ = 'actor'
    locals().update({
        f"{field}_uri": db.Column(db.String(64, 'utf8mb4_unicode_ci'), server_default=db.text("''"))
        for field in BaseMixin._sites
    })
    birthday = db.Column(db.Date, nullable=False, server_default=db.text("'1970-01-01'"))
    age = db.Column(db.Integer, server_default=db.text("'0'"))
    cupsize = db.Column(db.String(8, 'utf8mb4_unicode_ci'), server_default=db.text("''"))
    locals().update({
        metric: db.Column(db.Integer, server_default=db.text("'0'"))
        for metric in ['height', 'bust', 'waist', 'hip']
    })
    hometown = db.Column(db.String(128, 'utf8mb4_unicode_ci'), server_default=db.text("''"))
    hobby = db.Column(db.String(512, 'utf8mb4_unicode_ci'), server_default=db.text("''"))
    pic = db.Column(db.String(128, 'utf8mb4_unicode_ci'), server_default=db.text("''"))
    favorite = db.Column(db.SmallInteger, nullable=False, server_default=db.text("'0'"))
    movies = db.relationship("Movie", secondary=relation_tables['movie_actor'], back_populates="actors")


class DownloadFailure(DBBaseModel):
    __tablename__ = 'download_failure'

    magnet_id = db.Column(db.Integer, nullable=False, server_default=db.text("0"), comment='关联的磁力链接ID')
    movie_id = db.Column(db.Integer, nullable=False, server_default=db.text("0"), comment='关联的电影ID')
    censored_id = db.Column(db.String(64, 'utf8mb4_unicode_ci'), nullable=False, server_default=db.text("''"),
                            comment='电影识别码')
    magnet_xt = db.Column(db.String(768, 'utf8mb4_unicode_ci'), nullable=False, server_default=db.text("''"), unique=True, comment='磁力链接哈希')
    failure_reason = db.Column(db.String(512, 'utf8mb4_unicode_ci'), nullable=False, server_default=db.text("''"),
                               comment='失败原因')
    attempt_count = db.Column(db.Integer, nullable=False, server_default=db.text("1"), comment='尝试次数')
    last_attempt = db.Column(db.DateTime, nullable=False, server_default=db.text("CURRENT_TIMESTAMP"), comment='最后尝试时间')
    status = db.Column(db.Integer, nullable=False, server_default=db.text("0"), comment='状态：0=待重试，1=已重试成功，2=放弃重试')

    # You might want to add relationships if needed
    # magnet = db.relationship("MagnetModel", foreign_keys=[magnet_id])
    # movie = db.relationship("MovieModel", foreign_keys=[movie_id])