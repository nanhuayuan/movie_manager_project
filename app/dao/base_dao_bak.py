# app/dao/base_dao.py
import logging
from typing import Generic, TypeVar, Type, Optional, List, Dict, Any, Tuple
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from sqlalchemy import and_, or_, desc, asc
from sqlalchemy.orm import Query
from functools import wraps
import threading
from app.utils.db_util import db

# 类型变量T用于泛型编程
T = TypeVar('T')


class Singleton(type):
    """
    单例元类，用于实现线程安全的单例模式
    """
    _instances = {}
    _lock = threading.Lock()

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            with cls._lock:
                if cls not in cls._instances:
                    cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]


class BaseDAO(Generic[T], metaclass=Singleton):
    """
    数据访问对象的基类，提供通用的数据库操作方法

    使用元类实现单例模式，支持泛型
    所有继承此类的子类都将自动成为单例

    Attributes:
        model (Type[T]): 与DAO关联的数据模型类
    """

    def __init__(self, model: Type[T]):
        """
        初始化DAO实例

        Args:
            model (Type[T]): 与DAO关联的数据模型类
        """
        self.model = model

    def create(self, obj: T) -> T:
        """创建新的数据记录"""
        with db.session_scope() as session:
            try:
                session.add(obj)
                session.flush()  # 刷新以获取数据库生成的ID
                session.refresh(obj)  # 刷新对象以获取最新数据

                # 克隆对象的属性到新对象
                new_obj = self.model()
                for column in obj.__table__.columns:
                    setattr(new_obj, column.name, getattr(obj, column.name))

                # 确保在返回之前，所有需要的属性都已加载
                for relationship in obj.__mapper__.relationships:
                    if getattr(obj, relationship.key, None) is not None:
                        setattr(new_obj, relationship.key, getattr(obj, relationship.key))

                return new_obj
            except IntegrityError:
                session.rollback()
                logging.warning(f"IntegrityError while creating : {e}")
                raise e
            except SQLAlchemyError as e:
                session.rollback()
                raise e

    def batch_create(self, objects: List[T]) -> List[T]:
        """批量创建多条记录"""
        with db.session_scope() as session:
            try:
                for obj in objects:
                    session.add(obj)
                session.flush()

                # 确保所有对象都被刷新并获取生成的ID
                refreshed_objects = []
                for obj in objects:
                    session.refresh(obj)
                    refreshed_objects.append(self._clone_object(obj))

                return refreshed_objects
            except SQLAlchemyError as e:
                session.rollback()
                raise e

    def get_by_id(self, id: int) -> Optional[T]:
        """根据ID获取单条记录"""
        with db.session_scope() as session:
            obj =  session.query(self.model).filter(self.model.id == id).first()
            return self._clone_object(obj, session) if obj else None

    def get_all(self, page: int = 1, per_page: int = 10) -> Tuple[List[T], int]:
        with db.session_scope() as session:
            query = session.query(self.model)
            total = query.count()
            items = query.offset((page - 1) * per_page).limit(per_page).all()
            return self._clone_list(items, session), total
    def update(self, obj: T) -> T:
        """更新现有记录"""
        with db.session_scope() as session:
            try:
                # 确保对象与当前会话关联
                if obj not in session:
                    obj = session.merge(obj)

                session.flush()
                session.refresh(obj)

                # 克隆更新后的对象
                updated_obj = self.model()
                for column in obj.__table__.columns:
                    setattr(updated_obj, column.name, getattr(obj, column.name))

                # 复制关系属性
                for relationship in obj.__mapper__.relationships:
                    if getattr(obj, relationship.key, None) is not None:
                        setattr(updated_obj, relationship.key, getattr(obj, relationship.key))

                return updated_obj
            except SQLAlchemyError as e:
                session.rollback()
                raise e

    def delete(self, id: int) -> bool:
        """根据ID删除记录"""
        with db.session_scope() as session:
            obj = session.query(self.model).filter(self.model.id == id).first()
            if obj:
                session.delete(obj)
                return True
            return False

    def find_by_criteria(self, criteria: Dict[str, Any]) -> List[T]:
        """根据给定的条件查询记录"""
        with db.session_scope() as session:
            filters = [getattr(self.model, k) == v for k, v in criteria.items()]
            query_result = session.query(self.model).filter(and_(*filters)).all()
            return self._clone_list(query_result)

    def exists(self, id: int) -> bool:
        """检查指定ID的记录是否存在"""
        with db.session_scope() as session:
            return session.query(
                session.query(self.model).filter(self.model.id == id).exists()
            ).scalar()


    def count(self, criteria: Optional[Dict[str, Any]] = None) -> int:
        """统计记录数量"""
        with db.session_scope() as session:
            query = session.query(self.model)
            if criteria:
                filters = [getattr(self.model, k) == v for k, v in criteria.items()]
                query = query.filter(and_(*filters))
            return query.count()

    def get_or_create(self, defaults: Optional[Dict[str, Any]] = None, **kwargs) -> tuple[T, bool]:
        """获取记录，如果不存在则创建"""
        with db.session_scope() as session:
            instance = session.query(self.model).filter_by(**kwargs).first()
            if instance:
                return instance, False
            else:
                params = dict(kwargs)
                if defaults:
                    params.update(defaults)
                instance = self.model(**params)
                session.add(instance)
                session.flush()
                session.refresh(instance)
                return instance, True

        # 示例：处理复杂查询的方法

    def find_by_complex_criteria(self,
                                 filters: Dict[str, Any],
                                 order_by: Optional[str] = None,
                                 page: int = 1,
                                 per_page: int = 10) -> Tuple[List[T], int]:
        """
        使用复杂条件进行查询

        Args:
            filters: 过滤条件
            order_by: 排序字段
            page: 页码
            per_page: 每页数量

        Returns:
            Tuple[List[T], int]: 返回结果列表和总数
        """
        with db.session_scope() as session:
            query = session.query(self.model)

            # 应用过滤条件
            for key, value in filters.items():
                if value is not None:
                    query = query.filter(getattr(self.model, key) == value)

            # 计算总数
            total = query.count()

            # 应用排序
            if order_by:
                if order_by.startswith('-'):
                    query = query.order_by(desc(getattr(self.model, order_by[1:])))
                else:
                    query = query.order_by(asc(getattr(self.model, order_by)))

            # 应用分页
            items = query.offset((page - 1) * per_page).limit(per_page).all()

            # 克隆结果列表
            cloned_items = self._clone_list(items)

            return cloned_items, total
    def execute_query(self, query: Query) -> List[T]:
        """执行自定义查询并返回结果列表"""
        with db.session_scope() as session:
            # 将查询绑定到当前会话
            bound_query = query.with_session(session)
            results = bound_query.all()
            return self._clone_list(results)

    def _clone_object_old(self, obj: T, session) -> T:
        """克隆对象，确保返回的对象不与会话绑定"""
        if obj is None:
            return None

        new_obj = self.model()
        for column in obj.__table__.columns:
            setattr(new_obj, column.name, getattr(obj, column.name))

        # 可选：复制关系属性
        for relationship in obj.__mapper__.relationships:
            if getattr(obj, relationship.key, None) is not None:
                setattr(new_obj, relationship.key, getattr(obj, relationship.key))

        return new_obj

    def _clone_object(self, obj: T, session=None) -> T:
        if obj is None:
            return None

        new_obj = self.model()
        for column in obj.__table__.columns:
            setattr(new_obj, column.name, getattr(obj, column.name))

        # 只复制简单的关系属性，避免复杂的级联加载
        for relationship in obj.__mapper__.relationships:
            if relationship.uselist:
                continue  # 跳过多对多关系
            related_obj = getattr(obj, relationship.key, None)
            if related_obj:
                setattr(new_obj, relationship.key, related_obj)

        return new_obj
    def _clone_list(self, objects: List[T]) -> List[T]:
        """克隆对象列表，确保返回的所有对象都不与会话绑定"""
        return [self._clone_object(obj) for obj in objects]