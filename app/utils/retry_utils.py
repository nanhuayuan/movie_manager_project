import time
import functools
import random
from typing import Callable, Tuple, Type, Union, List, Optional
from app.config.log_config import info, error


def retry(max_retries: int = 3,
          exceptions: Union[Type[Exception], Tuple[Type[Exception], ...]] = Exception,
          delay: float = 1.0,
          backoff: float = 2.0,
          jitter: bool = True,
          on_retry: Optional[Callable] = None):
    """
    通用重试装饰器

    Args:
        max_retries: 最大重试次数
        exceptions: 捕获的异常类型，可以是单个异常类或元组
        delay: 初始延迟时间（秒）
        backoff: 退避倍数，每次重试后延迟时间会乘以这个值
        jitter: 是否添加随机抖动以避免同时重试
        on_retry: 重试前调用的回调函数，接收参数(exception, retry_count, next_delay)

    Returns:
        装饰器函数
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            retry_count = 0
            current_delay = delay

            while True:
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    retry_count += 1
                    if retry_count > max_retries:
                        error(f"函数 {func.__name__} 达到最大重试次数 {max_retries}，最后异常: {str(e)}")
                        raise

                    # 计算下次重试延迟
                    next_delay = current_delay
                    if jitter:
                        next_delay = current_delay * (1 + random.uniform(-0.1, 0.1))

                    # 调用回调函数
                    if on_retry:
                        on_retry(e, retry_count, next_delay)

                    error(f"函数 {func.__name__} 执行失败 (重试 {retry_count}/{max_retries}): {str(e)}，"
                          f"{next_delay:.2f}秒后重试")

                    # 等待后重试
                    time.sleep(next_delay)
                    current_delay *= backoff

        return wrapper

    return decorator


def retry_on_connection_error(max_retries: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """
    针对网络连接错误的重试装饰器

    使用方式简化，专门针对网络连接错误的重试场景
    """
    # 常见网络连接错误异常类型
    network_exceptions = (
        ConnectionError,
        TimeoutError,
        OSError,  # 包含网络相关错误
        Exception,  # 作为后备
    )

    return retry(
        max_retries=max_retries,
        exceptions=network_exceptions,
        delay=delay,
        backoff=backoff,
        jitter=True
    )


class RetryContext:
    """
    提供上下文管理器方式的重试

    用于需要更灵活控制重试流程的场景
    """

    def __init__(self, max_retries=3, delay=1.0, backoff=2.0,
                 exceptions=Exception, on_final_exception=None):
        self.max_retries = max_retries
        self.delay = delay
        self.backoff = backoff
        self.exceptions = exceptions
        self.on_final_exception = on_final_exception
        self.retry_count = 0

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            return True

        if not isinstance(exc_val, self.exceptions):
            return False

        self.retry_count += 1
        if self.retry_count > self.max_retries:
            if self.on_final_exception:
                self.on_final_exception(exc_val)
            return False

        next_delay = self.delay * (self.backoff ** (self.retry_count - 1))
        error(f"操作失败 (重试 {self.retry_count}/{self.max_retries}): {str(exc_val)}，"
              f"{next_delay:.2f}秒后重试")
        time.sleep(next_delay)

        # 返回True表示异常已处理，将重新执行with代码块
        return True