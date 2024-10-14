from typing import Generic, TypeVar, Type, Optional, List, Dict, Any, Tuple
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from sqlalchemy import and_, or_, desc, asc
from flask_sqlalchemy import SQLAlchemy
from flask import current_app

T = TypeVar('T')

class BaseDAO(Generic[T]):
    def __init__(self, model: Type[T]):
        self.model = model
        self.db: SQLAlchemy = self._get_db()

    @staticmethod
    def _get_db() -> SQLAlchemy:
        if 'sqlalchemy' in current_app.extensions:
            return current_app.extensions['sqlalchemy']
        elif hasattr(current_app, 'db'):
            return current_app.db
        else:
            raise RuntimeError("SQLAlchemy not found. Ensure it's properly initialized with Flask.")

    def create(self, obj: T) -> T:
        try:
            self.db.session.add(obj)
            self.db.session.commit()
            return obj
        except IntegrityError as e:
            self.db.session.rollback()
            current_app.logger.warning(f"IntegrityError while creating: {e}")
            raise
        except SQLAlchemyError as e:
            self.db.session.rollback()
            raise

    def batch_create(self, objects: List[T]) -> List[T]:
        try:
            self.db.session.add_all(objects)
            self.db.session.commit()
            return objects
        except SQLAlchemyError as e:
            self.db.session.rollback()
            raise

    def get_by_id(self, id: int) -> Optional[T]:
        return self.db.session.get(self.model, id)

    def get_all(self, page: int = 1, per_page: int = 10) -> Tuple[List[T], int]:
        query = self.db.session.query(self.model)
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        return pagination.items, pagination.total

    def update(self, obj: T) -> T:
        try:
            self.db.session.commit()
            return obj
        except SQLAlchemyError as e:
            self.db.session.rollback()
            raise

    def delete(self, id: int) -> bool:
        obj = self.get_by_id(id)
        if obj:
            try:
                self.db.session.delete(obj)
                self.db.session.commit()
                return True
            except SQLAlchemyError as e:
                self.db.session.rollback()
                raise
        return False

    def find_by_criteria(self, criteria: Dict[str, Any]) -> List[T]:
        filters = [getattr(self.model, k) == v for k, v in criteria.items()]
        return self.db.session.query(self.model).filter(and_(*filters)).all()

    def exists(self, id: int) -> bool:
        return self.db.session.query(self.model.query.filter_by(id=id).exists()).scalar()

    def count(self, criteria: Optional[Dict[str, Any]] = None) -> int:
        query = self.db.session.query(self.model)
        if criteria:
            filters = [getattr(self.model, k) == v for k, v in criteria.items()]
            query = query.filter(and_(*filters))
        return query.count()

    def get_or_create(self, defaults: Optional[Dict[str, Any]] = None, **kwargs) -> Tuple[T, bool]:
        instance = self.db.session.query(self.model).filter_by(**kwargs).first()
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
                raise

    def find_by_complex_criteria(self, filters: Dict[str, Any], order_by: Optional[str] = None,
                                 page: int = 1, per_page: int = 10) -> Tuple[List[T], int]:
        query = self.db.session.query(self.model)

        for key, value in filters.items():
            if value is not None:
                query = query.filter(getattr(self.model, key) == value)

        if order_by:
            if order_by.startswith('-'):
                query = query.order_by(desc(getattr(self.model, order_by[1:])))
            else:
                query = query.order_by(asc(getattr(self.model, order_by)))

        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        return pagination.items, pagination.total

    # The _clone_object and _clone_list methods remain unchanged

    # 保留 _clone_object 和 _clone_list 方法，它们在某些场景下可能仍然有用
    def _clone_object(self, obj: T) -> T:
        if obj is None:
            return None

        new_obj = self.model()
        for column in obj.__table__.columns:
            setattr(new_obj, column.name, getattr(obj, column.name))

        for relationship in obj.__mapper__.relationships:
            if not relationship.uselist:
                related_obj = getattr(obj, relationship.key, None)
                if related_obj:
                    setattr(new_obj, relationship.key, related_obj)

        return new_obj

    def _clone_list(self, objects: List[T]) -> List[T]:
        return [self._clone_object(obj) for obj in objects]