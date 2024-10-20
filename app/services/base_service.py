from typing import Generic, TypeVar, Type, Optional, List, Dict, Any, Tuple, Union
from app.utils.log_util import debug, info, warning, error, critical
from concurrent.futures import ThreadPoolExecutor
import functools
import time

# 定义泛型类型变量
T = TypeVar('T')  # 实体类型
D = TypeVar('D')  # DAO类型


class BaseService(Generic[T, D]):
    """
    基础服务类，提供通用的业务逻辑操作和增强功能。
    包含基础的CRUD操作、批量处理、缓存管理、异常处理等功能。

    泛型参数:
        T: 实体类型
        D: DAO类型
    """

    def __init__(self):
        # 从泛型参数获取实际的类型
        service_args = self.__class__.__orig_bases__[0].__args__
        model_class, dao_class = service_args[0], service_args[1]

        self.dao = dao_class()
        self.model_class = model_class
        self._thread_pool = ThreadPoolExecutor(max_workers=5)

    def _log_execution_time(func):
        """方法执行时间装饰器"""

        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            start_time = time.time()
            try:
                result = func(self, *args, **kwargs)
                end_time = time.time()
                debug(f"Method {func.__name__} executed in {end_time - start_time:.2f} seconds")
                return result
            except Exception as e:
                error(f"Error executing {func.__name__}: {str(e)}")
                raise

        return wrapper

    def _validate_entity(self, entity: T) -> bool:
        """
        验证实体对象的有效性

        Args:
            entity (T): 待验证的实体对象

        Returns:
            bool: 验证是否通过
        """
        try:
            if not isinstance(entity, self.model_class):
                raise ValueError(f"Entity must be instance of {self.model_class.__name__}")
            # 可以添加更多的验证逻辑
            return True
        except Exception as e:
            error(f"Entity validation failed: {str(e)}")
            return False

    @_log_execution_time
    def create(self, entity: T) -> Optional[T]:
        """
        创建实体对象

        Args:
            entity (T): 要创建的实体对象

        Returns:
            Optional[T]: 创建成功的实体对象，失败返回None
        """
        try:
            if self._validate_entity(entity):
                debug(f"Creating entity: {entity}")
                return self.dao.create(entity)
            return None
        except Exception as e:
            error(f"Failed to create entity: {str(e)}")
            return None

    @_log_execution_time
    def get_by_id(self, id: int) -> Optional[T]:
        """
        根据ID获取实体对象

        Args:
            id (int): 实体ID

        Returns:
            Optional[T]: 查找到的实体对象，不存在返回None
        """
        try:
            debug(f"Fetching entity with id: {id}")
            return self.dao.get_by_id(id)
        except Exception as e:
            error(f"Failed to get entity by id {id}: {str(e)}")
            return None

    def batch_get_by_ids(self, ids: List[int]) -> List[T]:
        """
        批量获取实体对象

        Args:
            ids (List[int]): ID列表

        Returns:
            List[T]: 实体对象列表
        """
        try:
            debug(f"Batch fetching entities with ids: {ids}")
            return self.dao.find_by_ids(ids)
        except Exception as e:
            error(f"Failed to batch get entities: {str(e)}")
            return []

    @_log_execution_time
    def update(self, entity: T) -> Optional[T]:
        """
        更新实体对象

        Args:
            entity (T): 要更新的实体对象

        Returns:
            Optional[T]: 更新后的实体对象，失败返回None
        """
        try:
            if self._validate_entity(entity):
                debug(f"Updating entity: {entity}")
                return self.dao.update(entity)
            return None
        except Exception as e:
            error(f"Failed to update entity: {str(e)}")
            return None

    def bulk_update(self, filter_criteria: Dict[str, Any], update_data: Dict[str, Any]) -> int:
        """
        批量更新实体对象

        Args:
            filter_criteria (Dict[str, Any]): 过滤条件
            update_data (Dict[str, Any]): 更新数据

        Returns:
            int: 更新的记录数
        """
        try:
            debug(f"Bulk updating entities with criteria: {filter_criteria}")
            return self.dao.bulk_update(filter_criteria, update_data)
        except Exception as e:
            error(f"Failed to bulk update entities: {str(e)}")
            return 0

    def delete(self, id: int) -> bool:
        """
        删除实体对象

        Args:
            id (int): 实体ID

        Returns:
            bool: 是否删除成功
        """
        try:
            debug(f"Deleting entity with id: {id}")
            return self.dao.delete(id)
        except Exception as e:
            error(f"Failed to delete entity with id {id}: {str(e)}")
            return False

    def get_paginated_list(self,
                           page: int = 1,
                           per_page: int = 10,
                           filters: Optional[Dict[str, Any]] = None,
                           order_by: Optional[str] = None) -> Tuple[List[T], int]:
        """
        获取分页列表

        Args:
            page (int): 页码
            per_page (int): 每页数量
            filters (Optional[Dict[str, Any]]): 过滤条件
            order_by (Optional[str]): 排序字段

        Returns:
            Tuple[List[T], int]: 实体对象列表和总数
        """
        try:
            debug(f"Fetching paginated list: page={page}, per_page={per_page}")
            return self.dao.find_by_complex_criteria(
                filters or {},
                order_by=order_by,
                page=page,
                per_page=per_page
            )
        except Exception as e:
            error(f"Failed to get paginated list: {str(e)}")
            return [], 0

    def execute_in_transaction(self, operations: List[callable]) -> bool:
        """
        在事务中执行多个操作

        Args:
            operations (List[callable]): 要执行的操作列表

        Returns:
            bool: 是否全部执行成功
        """
        try:
            # 这里假设DAO层有事务支持
            debug(f"Executing {len(operations)} operations in transaction")
            for operation in operations:
                operation()
            return True
        except Exception as e:
            error(f"Transaction failed: {str(e)}")
            return False

    async def async_batch_process(self, items: List[Any], process_func: callable) -> List[Any]:
        """
        异步批处理方法

        Args:
            items (List[Any]): 要处理的项目列表
            process_func (callable): 处理函数

        Returns:
            List[Any]: 处理结果列表
        """
        try:
            debug(f"Starting async batch process for {len(items)} items")
            futures = [self._thread_pool.submit(process_func, item) for item in items]
            return [future.result() for future in futures]
        except Exception as e:
            error(f"Async batch process failed: {str(e)}")
            return []

    def search(self,
               query: str,
               fields: List[str],
               page: int = 1,
               per_page: int = 10) -> Tuple[List[T], int]:
        """
        搜索实体对象

        Args:
            query (str): 搜索关键词
            fields (List[str]): 搜索字段
            page (int): 页码
            per_page (int): 每页数量

        Returns:
            Tuple[List[T], int]: 实体对象列表和总数
        """
        try:
            debug(f"Searching with query: {query} in fields: {fields}")
            filters = {field: query for field in fields}
            return self.dao.find_by_complex_criteria(filters, page=page, per_page=per_page)
        except Exception as e:
            error(f"Search failed: {str(e)}")
            return [], 0

    def validate_unique_fields(self, entity: T, fields: List[str]) -> bool:
        """
        验证字段唯一性

        Args:
            entity (T): 实体对象
            fields (List[str]): 要验证的字段列表

        Returns:
            bool: 是否唯一
        """
        try:
            debug(f"Validating unique fields: {fields}")
            for field in fields:
                criteria = {field: getattr(entity, field)}
                if self.dao.find_by_criteria(criteria):
                    return False
            return True
        except Exception as e:
            error(f"Unique field validation failed: {str(e)}")
            return False

    @_log_execution_time
    def get_by_name(self,
                    name: str,
                    fuzzy_match: bool = False,
                    case_sensitive: bool = True) -> Union[Optional[T], List[T]]:
        """
        根据名称获取实体对象，支持模糊匹配和大小写敏感选项

        Args:
            name (str): 要查询的名称
            fuzzy_match (bool): 是否使用模糊匹配，True则返回List[T]，False则返回Optional[T]
            case_sensitive (bool): 是否大小写敏感

        Returns:
            Union[Optional[T], List[T]]:
                - 精确匹配模式下返回单个对象或None
                - 模糊匹配模式下返回对象列表
        """
        try:
            if not name or not isinstance(name, str):
                warning(f"Invalid name parameter: {name}")
                return [] if fuzzy_match else None

            debug(f"Searching entity by name: {name} (fuzzy_match={fuzzy_match}, case_sensitive={case_sensitive})")

            # 处理大小写
            processed_name = name if case_sensitive else name.lower()

            if fuzzy_match:
                # 模糊匹配模式
                if hasattr(self.model_class, 'name'):
                    filters = {
                        'name': f"%{processed_name}%"  # 使用like查询
                    }
                    results = self.dao.find_by_criteria(filters)

                    # 如果不区分大小写，需要在内存中再次过滤
                    if not case_sensitive:
                        results = [
                            entity for entity in results
                            if processed_name in getattr(entity, 'name', '').lower()
                        ]

                    debug(f"Found {len(results)} entities with fuzzy name match")
                    return results
                else:
                    warning(f"Model {self.model_class.__name__} does not have 'name' attribute")
                    return []
            else:
                # 精确匹配模式
                result = self.dao.get_by_name(name)
                if result:
                    # 处理大小写不敏感的情况
                    if not case_sensitive and getattr(result, 'name', '').lower() != processed_name:
                        return None
                    debug(f"Found entity with exact name match: {result}")
                else:
                    debug(f"No entity found with exact name: {name}")
                return result

        except Exception as e:
            error(f"Error in get_by_name: {str(e)}")
            return [] if fuzzy_match else None

    def get_by_names(self,
                     names: List[str],
                     match_all: bool = True) -> List[T]:
        """
        批量根据名称获取实体对象列表

        Args:
            names (List[str]): 要查询的名称列表
            match_all (bool): True表示必须所有名称都匹配，False表示匹配任一名称

        Returns:
            List[T]: 查找到的实体对象列表
        """
        try:
            if not names or not isinstance(names, list):
                warning(f"Invalid names parameter: {names}")
                return []

            debug(f"Batch searching entities by names: {names}")

            # 使用 IN 查询获取所有可能的匹配
            if hasattr(self.model_class, 'name'):
                found_entities = self.dao.find_by_criteria({'name': names})

                if not found_entities:
                    debug(f"No entities found for names: {names}")
                    return []

                if match_all:
                    # 确保所有名称都有匹配的实体
                    found_names = {getattr(entity, 'name', '') for entity in found_entities}
                    if not all(name in found_names for name in names):
                        debug(f"Not all names were matched. Found names: {found_names}")
                        return []

                debug(f"Found {len(found_entities)} entities matching the names criteria")
                return found_entities
            else:
                warning(f"Model {self.model_class.__name__} does not have 'name' attribute")
                return []

        except Exception as e:
            error(f"Error in get_by_names: {str(e)}")
            return []