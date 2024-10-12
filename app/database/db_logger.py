# myproject/database/db_logger.py
import logging
import time
from functools import wraps
from typing import Any, Callable, Dict, Optional

# 创建专门的数据库日志记录器
db_logger = logging.getLogger('database')


class SQLLogFormatter(logging.Formatter):
    """自定义的 SQL 日志格式化器"""

    def format(self, record: logging.LogRecord) -> str:
        """格式化日志记录

        为不同类型的 SQL 操作添加特定的格式
        """
        # 如果存在，获取额外的属性
        duration = getattr(record, 'duration', None)
        params = getattr(record, 'params', None)

        # 基本日志信息
        log_message = super().format(record)

        # 添加参数和持续时间信息（如果存在）
        if params:
            log_message += f"\nParameters: {params}"
        if duration:
            log_message += f"\nDuration: {duration:.4f}s"

        return log_message


def setup_db_logger(log_config: Dict[str, Any]) -> None:
    """设置数据库日志记录器

    Args:
        log_config: 日志配置字典
    """
    # 设置日志级别
    db_logger.setLevel(log_config.get('level', logging.INFO))

    # 创建并配置文件处理器
    file_handler = logging.FileHandler(
        filename=log_config.get('filename', 'sql.log'),
        encoding='utf-8'
    )
    file_handler.setFormatter(SQLLogFormatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    ))
    db_logger.addHandler(file_handler)

    # 可选：添加控制台处理器用于开发调试
    if log_config.get('console_output', False):
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(SQLLogFormatter(
            '%(levelname)s - %(message)s'
        ))
        db_logger.addHandler(console_handler)


def log_sql(level: int = logging.INFO) -> Callable:
    """用于记录 SQL 操作的装饰器

    Args:
        level: 日志级别，默认为 INFO

    Returns:
        装饰器函数
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # 提取 SQL 查询（假设是第一个参数）
            sql = args[0] if args else kwargs.get('sql', 'No SQL provided')

            # 记录开始时间
            start_time = time.time()

            try:
                # 执行数据库操作
                result = func(*args, **kwargs)

                # 计算持续时间
                duration = time.time() - start_time

                # 记录成功的操作
                db_logger.log(
                    level,
                    f"SQL Query Executed Successfully: {sql}",
                    extra={
                        'duration': duration,
                        'params': kwargs.get('params', None)
                    }
                )

                return result

            except Exception as e:
                # 记录失败的操作
                db_logger.error(
                    f"SQL Query Failed: {sql}",
                    extra={
                        'duration': time.time() - start_time,
                        'params': kwargs.get('params', None),
                        'error': str(e)
                    },
                    exc_info=True
                )
                raise

        return wrapper

    return decorator


