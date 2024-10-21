from typing import List, Optional, Dict, Any, Callable
from app.config.log_config import debug, info, warning, error, critical
import time
from functools import wraps


class RetryUtil:
    @staticmethod
    def retry_on_exception(
            max_attempts: int = 3,
            delay: float = 2.0,
            exceptions: tuple = (Exception,)
    ) -> Callable:
        """
        重试装饰器

        Args:
            max_attempts: 最大重试次数
            delay: 重试间隔（秒）
            exceptions: 需要重试的异常类型
        """

        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                last_exception = None
                for attempt in range(max_attempts):
                    try:
                        return func(*args, **kwargs)
                    except exceptions as e:
                        last_exception = e
                        if attempt < max_attempts - 1:  # 不是最后一次尝试
                            warning(f"第 {attempt + 1} 次尝试失败: {str(e)}，{delay}秒后重试...")
                            time.sleep(delay)
                        else:
                            error(f"重试 {max_attempts} 次后仍然失败: {str(e)}")
                raise last_exception

            return wrapper

        return decorator
