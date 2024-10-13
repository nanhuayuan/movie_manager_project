import logging
from typing import Generic, TypeVar, Type, Optional, List, Dict, Any, Tuple
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from sqlalchemy import and_, or_, desc, asc
from flask_sqlalchemy import Pagination
from app.utils.db_util import get_db

T = TypeVar('T')

class BaseDAO(Generic[T]):
    def __init__(self, model: Type[T]):
        self.model = model
        self.db = get_db()

    def create(self, obj: T) -> T:
        try:
            self.db.session.add(obj)
            self.db.session.commit()
            return obj
        except IntegrityError as e:
            self.db.session.rollback()
            logging.warning(f"IntegrityError while creating: {e}")
            raise e
        except SQLAlchemyError as e:
            self.db.session.rollback()
            raise e

    def batch_create(self, objects: List[T]) -> List[T]:
        try:
            self.db.session.add_all(objects)
            self.db.session.commit()
            return objects
        except SQLAlchemyError as e:
            self.db.session.rollback()
            raise e

    def get_by_id(self, id: int) -> Optional[T]:
        return self.model.query.get(id)

    def get_all(self, page: int = 1, per_page: int = 10) -> Tuple[List[T], int]:
        pagination: Pagination = self.model.query.paginate(page=page, per_page=per_page, error_out=False)
        return pagination.items, pagination.total

    def update(self, obj: T) -> T:
        try:
            self.db.session.commit()
            return obj
        except SQLAlchemyError as e:
            self.db.session.rollback()
            raise e

    def delete(self, id: int) -> bool:
        obj = self.get_by_id(id)
        if obj:
            try:
                self.db.session.delete(obj)
                self.db.session.commit()
                return True
            except SQLAlchemyError as e:
                self.db.session.rollback()
                raise e
        return False

    def find_by_criteria(self, criteria: Dict[str, Any]) -> List[T]:
        filters = [getattr(self.model, k) == v for k, v in criteria.items()]
        return self.model.query.filter(and_(*filters)).all()

    def exists(self, id: int) -> bool:
        return self.db.session.query(self.model.query.filter_by(id=id).exists()).scalar()

    def count(self, criteria: Optional[Dict[str, Any]] = None) -> int:
        query = self.model.query
        if criteria:
            filters = [getattr(self.model, k) == v for k, v in criteria.items()]
            query = query.filter(and_(*filters))
        return query.count()

    def get_or_create(self, defaults: Optional[Dict[str, Any]] = None, **kwargs) -> Tuple[T, bool]:
        instance = self.model.query.filter_by(**kwargs).first()
        if instance:
            return instance, False
        else:
            params = dict(kwargs)
            if defaults:
                params.update(defaults)
            instance = self.model(**params)
            try:
                self.db.session.add(instance)
                self.db.session.commit()
                return instance, True
            except SQLAlchemyError as e:
                self.db.session.rollback()
                raise e

    def find_by_complex_criteria(self, filters: Dict[str, Any], order_by: Optional[str] = None,
                                 page: int = 1, per_page: int = 10) -> Tuple[List[T], int]:
        query = self.model.query

        for key, value in filters.items():
            if value is not None:
                query = query.filter(getattr(self.model, key) == value)

        if order_by:
            if order_by.startswith('-'):
                query = query.order_by(desc(getattr(self.model, order_by[1:])))
            else:
                query = query.order_by(asc(getattr(self.model, order_by)))

        pagination: Pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        return pagination.items, pagination.total