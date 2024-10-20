# 基本使用
from app.utils.retry_util import RetryUtil


@RetryUtil.retry_on_exception()
def some_function():
    # 函数实现

# 自定义重试参数
@RetryUtil.retry_on_exception(max_attempts=5, delay=1.0)
def another_function():
    # 函数实现

# 指定异常类型
@RetryUtil.retry_on_exception(exceptions=(ValueError, ConnectionError))
def specific_function():
    # 函数实现