from typing import Generic, TypeVar, Optional, List, Dict, Any, Tuple, Union
from concurrent.futures import ThreadPoolExecutor
import functools
import time
from app.config.log_config import debug, error

T, D = TypeVar('T'), TypeVar('D')

class BaseService(Generic[T, D]):
    def __init__(self):
        service_args = self.__class__.__orig_bases__[0].__args__
        self.model_class, dao_class = service_args
        self.dao = dao_class()
        self._thread_pool = ThreadPoolExecutor(max_workers=5)

    def _log_exec_time(func):
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            start = time.time()
            result = func(self, *args, **kwargs)
            debug(f"{func.__name__} executed in {time.time() - start:.2f}s")
            return result
        return wrapper

    def _validate_entity(self, entity: T) -> bool:
        return isinstance(entity, self.model_class)

    @_log_exec_time
    def create(self, entity: T) -> Optional[T]:
        return self.dao.create(entity) if self._validate_entity(entity) else None

    @_log_exec_time
    def get_by_id(self, id: int, options: List[Any] = None) -> Optional[T]:
        return self.dao.get_by_id(id, options)

    def get_by_field(self, field: str, value: Any, options: List[Any] = None) -> Optional[T]:
        return self.dao.get_by_field(field, value, options)

    def batch_get_by_ids(self, ids: List[int], options: List[Any] = None) -> List[T]:
        return self.dao.find_by_ids(ids, options)

    @_log_exec_time
    def update(self, entity: T) -> Optional[T]:
        return self.dao.update(entity) if self._validate_entity(entity) else None

    def bulk_update(self, filter_criteria: Dict[str, Any], update_data: Dict[str, Any]) -> int:
        return self.dao.bulk_update(filter_criteria, update_data)

    def delete(self, id: int) -> bool:
        return self.dao.delete(id)

    def get_paginated_list(self, page: int = 1, per_page: int = 10,
                          filters: Optional[Dict[str, Any]] = None,
                          order_by: Optional[str] = None,
                          options: List[Any] = None) -> Tuple[List[T], int]:
        return self.dao.find_by_complex_criteria(filters or {}, order_by, page, per_page, options)

    async def async_batch_process(self, items: List[Any], process_func: callable) -> List[Any]:
        futures = [self._thread_pool.submit(process_func, item) for item in items]
        return [future.result() for future in futures]

    def get_by_name(self, name: str, options: List[Any] = None) -> Optional[T]:
        return self.dao.get_by_name(name, options)

    def search(self, query: str, fields: List[str],
              page: int = 1, per_page: int = 10,
              options: List[Any] = None) -> Tuple[List[T], int]:
        debug(f"Searching with query: {query} in fields: {fields}")
        filters = {field: query for field in fields}
        return self.dao.find_by_complex_criteria(filters, page=page, per_page=per_page, options=options)