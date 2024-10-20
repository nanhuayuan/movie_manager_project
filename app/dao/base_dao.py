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
    提供了完整的CRUD操作和高级查询功能
    """

    def __init__(self):
        # 通过泛型参数获取实际的类型
        self.model = self.__class__.__orig_bases__[0].__args__[0]
        self.db: SQLAlchemy = self._get_db()
        info(f"BaseDAO initialized for model: {self.model.__name__}")

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
        """
        批量创建对象
        Args:
            objects (List[T]): 要创建的对象列表
        Returns:
            List[T]: 创建成功的对象列表
        """
        try:
            debug(f"Batch creating {len(objects)} {self.model.__name__} objects")
            # 这个可用吗 self.db.session.add_all(objects)
            self.db.session.bulk_save_objects(objects)
            self.db.session.commit()
            info(f"Batch created {len(objects)} objects successfully")
            return objects
        except Exception as e:
            error(f"Error in batch create: {str(e)}")
            self.db.session.rollback()
            raise

    def get_by_id(self, id: int) -> Optional[T]:
        """
        根据ID获取对象
        Args:
            id (int): 对象ID
        Returns:
            Optional[T]: 查找到的对象或None
        """
        try:
            return self.db.session.get(self.model, id)
        except Exception as e:
            error(f"Error in get_by_id: {str(e)}")
            raise

    def get_by_name(self, name: str) -> Optional[T]:
        """
        根据名称获取对象
        Args:
            name (str): 对象名称
        Returns:
            Optional[T]: 查找到的对象或None
        """
        try:
            return self.db.session.query(self.model).filter_by(name=name).first()
        except Exception as e:
            error(f"Error in get_by_name: {str(e)}")
            raise

    def get_all(self, page: int = 1, per_page: int = 10) -> Tuple[List[T], int]:
        """
        获取所有对象（分页）
        Args:
            page (int): 页码
            per_page (int): 每页数量
        Returns:
            Tuple[List[T], int]: 对象列表和总数
        """
        try:
            pagination = self.db.session.query(self.model).paginate(
                page=page, per_page=per_page, error_out=False
            )
            return pagination.items, pagination.total
        except Exception as e:
            error(f"Error in get_all: {str(e)}")
            raise

    def update(self, obj: T) -> T:
        """
        更新对象
        Args:
            obj (T): 要更新的对象
        Returns:
            T: 更新后的对象
        """
        try:
            self.db.session.commit()
            return obj
        except Exception as e:
            error(f"Error updating {self.model.__name__}: {str(e)}")
            self.db.session.rollback()
            raise

    def update_by_id(self, id: int, update_dict: Dict[str, Any]) -> Optional[T]:
        """
        根据ID更新对象
        Args:
            id (int): 对象ID
            update_dict (Dict[str, Any]): 要更新的字段和值
        Returns:
            Optional[T]: 更新后的对象或None
        """
        try:
            obj = self.get_by_id(id)
            if obj:
                for key, value in update_dict.items():
                    setattr(obj, key, value)
                self.db.session.commit()
                return obj
            return None
        except Exception as e:
            error(f"Error in update_by_id: {str(e)}")
            self.db.session.rollback()
            raise


    def delete(self, id: int) -> bool:
        """
        删除对象
        Args:
            id (int): 对象ID
        Returns:
            bool: 是否删除成功
        """
        try:
            obj = self.get_by_id(id)
            if obj:
                self.db.session.delete(obj)
                self.db.session.commit()
                return True
            return False
        except Exception as e:
            error(f"Error in delete: {str(e)}")
            self.db.session.rollback()
            raise

    def find_by_criteria(self, criteria: Dict[str, Any]) -> List[T]:
        """
        根据条件查找对象
        Args:
            criteria (Dict[str, Any]): 查询条件
        Returns:
            List[T]: 符合条件的对象列表
        """
        try:
            filters = [getattr(self.model, k) == v for k, v in criteria.items()]
            return self.db.session.query(self.model).filter(and_(*filters)).all()
        except AttributeError as e:
            error(f"Invalid attribute in criteria: {str(e)}")
            raise
        except Exception as e:
            error(f"Database error in find_by_criteria: {str(e)}")
            raise

    def find_one_by_criteria(self, criteria: Dict[str, Any]) -> Optional[T]:
        """
        根据等值条件查找单个对象
        Args:
            criteria (Dict[str, Any]): 查询条件字典,key为属性名,value为查询值
        Returns:
            Optional[T]: 符合条件的对象,未找到时返回None
        Raises:
            Exception: 查询过程中的任何错误
        """
        try:
            filters = [getattr(self.model, k) == v for k, v in criteria.items()]
            return self.db.session.query(self.model).filter(and_(*filters)).first()
        except AttributeError as e:
            error(f"Invalid attribute in criteria: {str(e)}")
            raise
        except Exception as e:
            error(f"Database error in find_one_by_criteria: {str(e)}")
            raise

    def exists(self, id: int) -> bool:
        """
        检查对象是否存在
        Args:
            id (int): 对象ID
        Returns:
            bool: 是否存在
        """
        try:
            return self.db.session.query(
                self.model.query.filter_by(id=id).exists()
            ).scalar()
        except Exception as e:
            error(f"Error in exists: {str(e)}")
            raise

    def count(self, criteria: Optional[Dict[str, Any]] = None) -> int:
        """
        计算符合条件的对象数量
        Args:
            criteria (Optional[Dict[str, Any]]): 查询条件
        Returns:
            int: 对象数量
        """
        try:
            query = self.db.session.query(self.model)
            if criteria:
                filters = [getattr(self.model, k) == v for k, v in criteria.items()]
                query = query.filter(and_(*filters))
            return query.count()
        except Exception as e:
            error(f"Error in count: {str(e)}")
            raise

    def get_or_create(self, defaults: Optional[Dict[str, Any]] = None, **kwargs) -> Tuple[T, bool]:
        """
        获取对象，如不存在则创建
        Args:
            defaults (Optional[Dict[str, Any]]): 创建时的默认值
            **kwargs: 查询条件
        Returns:
            Tuple[T, bool]: 对象和是否新创建的标志
        """
        try:
            instance = self.db.session.query(self.model).filter_by(**kwargs).first()
            if instance:
                return instance, False
            else:
                params = dict(kwargs)
                if defaults:
                    params.update(defaults)
                instance = self.model(**params)
                self.db.session.add(instance)
                self.db.session.commit()
                return instance, True
        except Exception as e:
            error(f"Error in get_or_create: {str(e)}")
            self.db.session.rollback()
            raise

    def find_by_complex_criteria(
        self,
        filters: Dict[str, Any],
        order_by: Optional[str] = None,
        page: int = 1,
        per_page: int = 10
    ) -> Tuple[List[T], int]:
        """
        复杂条件查询
        Args:
            filters (Dict[str, Any]): 过滤条件
            order_by (Optional[str]): 排序字段
            page (int): 页码
            per_page (int): 每页数量
        Returns:
            Tuple[List[T], int]: 对象列表和总数
        """
        try:
            query = self.db.session.query(self.model)

            # 应用过滤条件
            for key, value in filters.items():
                if isinstance(value, (list, tuple)):
                    query = query.filter(getattr(self.model, key).in_(value))
                elif isinstance(value, dict):
                    for op, val in value.items():
                        if op == 'gt':
                            query = query.filter(getattr(self.model, key) > val)
                        elif op == 'lt':
                            query = query.filter(getattr(self.model, key) < val)
                        elif op == 'gte':
                            query = query.filter(getattr(self.model, key) >= val)
                        elif op == 'lte':
                            query = query.filter(getattr(self.model, key) <= val)
                        elif op == 'like':
                            query = query.filter(getattr(self.model, key).like(f"%{val}%"))
                        elif op == 'ilike':
                            query = query.filter(getattr(self.model, key).ilike(f"%{val}%"))
                else:
                    query = query.filter(getattr(self.model, key) == value)

            # 应用排序
            if order_by:
                if order_by.startswith('-'):
                    query = query.order_by(desc(getattr(self.model, order_by[1:])))
                else:
                    query = query.order_by(asc(getattr(self.model, order_by)))

            # 执行分页查询
            pagination = query.paginate(page=page, per_page=per_page, error_out=False)
            return pagination.items, pagination.total
        except Exception as e:
            error(f"Error in find_by_complex_criteria: {str(e)}")
            raise
    def execute_query(self, query: Query) -> List[T]:
        """
        执行自定义查询
        Args:
            query (Query): SQLAlchemy查询对象
        Returns:
            List[T]: 查询结果列表
        """
        try:
            return query.all()
        except Exception as e:
            error(f"Error in execute_query: {str(e)}")
            raise
    def bulk_update(self, filter_dict: Dict[str, Any], update_dict: Dict[str, Any]) -> int:
        """
        批量更新
        Args:
            filter_dict (Dict[str, Any]): 过滤条件
            update_dict (Dict[str, Any]): 要更新的字段和值
        Returns:
            int: 更新的记录数
        """
        try:
            query = self.db.session.query(self.model)
            for key, value in filter_dict.items():
                query = query.filter(getattr(self.model, key) == value)
            count = query.update(update_dict)
            self.db.session.commit()
            return count
        except Exception as e:
            error(f"Error in bulk_update: {str(e)}")
            self.db.session.rollback()
            raise

    def find_by_ids(self, ids: List[int]) -> List[T]:
        """
        根据ID列表批量查询
        Args:
            ids (List[int]): ID列表
        Returns:
            List[T]: 对象列表
        """
        try:
            return self.db.session.query(self.model).filter(self.model.id.in_(ids)).all()
        except Exception as e:
            error(f"Error in find_by_ids: {str(e)}")
            raise