from typing import Generic, TypeVar, Type, Optional, List, Dict, Any, Tuple
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

    # ... [其他方法的实现，每个方法都添加类似的注释和日志记录] ...

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