# app/dao/base_dao.py
from sqlalchemy.orm import Session
from typing import Generic, TypeVar, Type
from sqlalchemy.exc import SQLAlchemyError
#rom app.utils.database import db

T = TypeVar('T')

class BaseDAO(Generic[T]):
    def __init__(self, model: Type[T]):
        self.model = model

    def create(self, obj: T) -> T:
        try:
            db.session.add(obj)
            db.session.commit()
            return obj
        except SQLAlchemyError as e:
            db.session.rollback()
            raise e

    def get_by_id(self, id: int) -> T:
        return db.session.query(self.model).filter(self.model.id == id).first()

    def get_all(self) -> list[T]:
        return db.session.query(self.model).all()

    def update(self, obj: T) -> T:
        try:
            db.session.merge(obj)
            db.session.commit()
            return obj
        except SQLAlchemyError as e:
            db.session.rollback()
            raise e

    def delete(self, id: int) -> bool:
        try:
            obj = self.get_by_id(id)
            if obj:
                db.session.delete(obj)
                db.session.commit()
                return True
            return False
        except SQLAlchemyError as e:
            db.session.rollback()
            raise e