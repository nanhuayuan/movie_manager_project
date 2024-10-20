from typing import Generic, TypeVar, Type, Optional, List, Dict, Any, Tuple

from flask_sqlalchemy.query import Query
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from sqlalchemy import and_, or_, desc, asc
from flask_sqlalchemy import SQLAlchemy
from flask import current_app
from app.utils.log_util import debug, info, warning, error, critical

T = TypeVar('T')


class BaseDAO(Generic[T]):
    """
    基础数据访问对象，提供通用的数据库操作方法

    泛型参数 T 表示与之关联的模型类型
    """

    def __init__(self, model: Type[T]):
        """
        初始化BaseDAO

        Args:
            model (Type[T]): 与DAO关联的模型类

        日志记录：
        - 记录BaseDAO的初始化
        """
        self.model = model
        self.db: SQLAlchemy = self._get_db()
        info(f"BaseDAO initialized for model: {model.__name__}")

    @staticmethod
    def _get_db() -> SQLAlchemy:
        """
        获取SQLAlchemy实例

        Returns:
            SQLAlchemy: Flask应用的SQLAlchemy实例

        Raises:
            RuntimeError: 如果未找到SQLAlchemy实例

        日志记录：
        - 记录获取SQLAlchemy实例的尝试
        - 记录可能发生的错误
        """
        debug("Attempting to get SQLAlchemy instance")
        if 'sqlalchemy' in current_app.extensions:
            return current_app.extensions['sqlalchemy']
        elif hasattr(current_app, 'db'):
            return current_app.db
        else:
            error("SQLAlchemy not found. Ensure it's properly initialized with Flask.")
            raise RuntimeError("SQLAlchemy not found. Ensure it's properly initialized with Flask.")

    def create(self, obj: T) -> T:
        """
        创建新对象

        Args:
            obj (T): 要创建的对象

        Returns:
            T: 创建成功后的对象

        Raises:
            IntegrityError: 如果违反完整性约束
            SQLAlchemyError: 如果发生其他数据库错误

        日志记录：
        - 记录创建对象的尝试
        - 记录创建成功或失败的情况
        """
        try:
            debug(f"Attempting to create new {self.model.__name__} object")
            self.db.session.add(obj)
            self.db.session.commit()
            info(f"Successfully created new {self.model.__name__} object")
            return obj
        except IntegrityError as e:
            error(f"IntegrityError while creating {self.model.__name__}: {e}")
            self.db.session.rollback()
            raise
        except SQLAlchemyError as e:
            error(f"SQLAlchemyError while creating {self.model.__name__}: {e}")
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

    def get_by_name(self, name: str) -> Optional[T]:
        return self.db.session.query(T).filter(T.name == name).first()

    def get_all(self, page: int = 1, per_page: int = 10) -> Tuple[List[T], int]:
        query = self.db.session.query(self.model)
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        return pagination.items, pagination.total

    def update(self, obj: T) -> T:
        try:
            self.db.session.commit()
            return obj
        except SQLAlchemyError as e:
            error(f"IntegrityError while creating {self.model.__name__}: {e}")
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
        """
        根据复杂条件查找对象

        Args:
            filters (Dict[str, Any]): 过滤条件
            order_by (Optional[str]): 排序字段
            page (int): 页码
            per_page (int): 每页数量


        Returns:
            Tuple[List[T], int]: 符合条件的对象列表和总数

        日志记录：
        - 记录复杂查询的尝试
        - 记录查询结果的数量
        """
        debug(f"Attempting complex query for {self.model.__name__} with filters: {filters}")
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
        info(f"Complex query for {self.model.__name__} returned {pagination.total} results")
        return pagination.items, pagination.total

    def execute_query(self, query: Query) -> List[T]:
        """执行自定义查询并返回结果列表"""
        with db.session_scope() as session:
            # 将查询绑定到当前会话
            bound_query = query.with_session(session)
            results = bound_query.all()
            return results
