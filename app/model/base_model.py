
from decimal import Decimal

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Column, Integer, String, Date, DateTime, Float, ForeignKey, BigInteger
from app.utils.db_util import db
from datetime import datetime, time, date

class BaseModel():
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