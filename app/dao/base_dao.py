from typing import Generic, TypeVar, Optional, List, Dict, Any, Tuple, Union
from flask_sqlalchemy.query import Query
from sqlalchemy import and_, desc, asc
from sqlalchemy.orm import joinedload
from flask_sqlalchemy import SQLAlchemy
from flask import current_app
from app.config.log_config import debug, error

T = TypeVar('T')

class BaseDAO(Generic[T]):
    def __init__(self):
        self.model = self.__class__.__orig_bases__[0].__args__[0]
        self.db: SQLAlchemy = current_app.extensions.get('sqlalchemy') or getattr(current_app, 'db', None)
        if not self.db:
            raise RuntimeError("SQLAlchemy not initialized")

    def create(self, obj: T) -> T:
        self.db.session.add(obj)
        self.db.session.commit()
        return obj

    def batch_create(self, objects: List[T]) -> List[T]:
        self.db.session.bulk_save_objects(objects)
        self.db.session.commit()
        return objects

    def get_by_id(self, id: int, options: List[Any] = None) -> Optional[T]:
        query = self.db.session.query(self.model)
        if options:
            for option in options:
                query = query.options(option)
        return query.get(id)

    def find_by_ids(self, ids: List[int], options: List[Any] = None) -> List[T]:
        query = self.db.session.query(self.model).filter(self.model.id.in_(ids))
        if options:
            for option in options:
                query = query.options(option)
        return query.all()

    def get_by_field(self, field: str, value: Any, options: List[Any] = None) -> Optional[T]:
        query = self.db.session.query(self.model).filter(getattr(self.model, field) == value)
        if options:
            for option in options:
                query = query.options(option)
        return query.first()

    def get_by_name(self, name: str, options: List[Any] = None) -> Optional[T]:
        return self.get_by_field('name', name, options)

    def get_all(self, page: int = 1, per_page: int = 10, options: List[Any] = None) -> Tuple[List[T], int]:
        query = self.db.session.query(self.model)
        if options:
            for option in options:
                query = query.options(option)
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        return pagination.items, pagination.total

    def find_by_criteria(self, criteria: Dict[str, Any], options: List[Any] = None, one: bool = False) -> Union[Optional[T], List[T]]:
        query = self.db.session.query(self.model)
        if options:
            for option in options:
                query = query.options(option)
        filters = [getattr(self.model, k) == v for k, v in criteria.items()]
        query = query.filter(and_(*filters))
        return query.first() if one else query.all()

    def find_by_complex_criteria(self, filters: Dict[str, Any], order_by: Optional[str] = None,
                               page: int = 1, per_page: int = 10, options: List[Any] = None) -> Tuple[List[T], int]:
        query = self.db.session.query(self.model)
        if options:
            for option in options:
                query = query.options(option)

        for key, value in filters.items():
            if isinstance(value, (list, tuple)):
                query = query.filter(getattr(self.model, key).in_(value))
            elif isinstance(value, dict):
                for op, val in value.items():
                    attr = getattr(self.model, key)
                    query = query.filter({
                        'gt': attr > val,
                        'lt': attr < val,
                        'gte': attr >= val,
                        'lte': attr <= val,
                        'like': attr.like(f"%{val}%"),
                        'ilike': attr.ilike(f"%{val}%")
                    }.get(op, attr == val))
            else:
                query = query.filter(getattr(self.model, key) == value)

        if order_by:
            query = query.order_by(desc(getattr(self.model, order_by[1:]))
                                 if order_by.startswith('-')
                                 else asc(getattr(self.model, order_by)))

        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        return pagination.items, pagination.total

    def update(self, obj: T) -> T:
        self.db.session.commit()
        return obj

    def delete(self, id: int) -> bool:
        obj = self.get_by_id(id)
        if obj:
            self.db.session.delete(obj)
            self.db.session.commit()
            return True
        return False

    def bulk_update(self, filter_dict: Dict[str, Any], update_dict: Dict[str, Any]) -> int:
        query = self.db.session.query(self.model)
        for key, value in filter_dict.items():
            query = query.filter(getattr(self.model, key) == value)
        count = query.update(update_dict)
        self.db.session.commit()
        return count

    def exists(self, id: int) -> bool:
        return self.db.session.query(self.model.query.filter_by(id=id).exists()).scalar()

    def count(self, criteria: Optional[Dict[str, Any]] = None) -> int:
        query = self.db.session.query(self.model)
        if criteria:
            filters = [getattr(self.model, k) == v for k, v in criteria.items()]
            query = query.filter(and_(*filters))
        return query.count()