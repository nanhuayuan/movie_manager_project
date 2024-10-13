from app.config.log_config import load_logging_config

# 加载日志配置
load_logging_config()

# 其他导入和初始化代码
import logging

# 创建 logger 实例
logger = logging.getLogger('fileAndConsole')

# 使用 logger
logger.debug('Debug message')
logger.info('Info message')

# 假设在一个业务逻辑文件中

# 获取配置中的 fileAndConsole logger
import logging
logger = logging.getLogger('fileAndConsole')


def some_business_logic():
    logger.info("业务逻辑开始执行")

    try:
        # 一些业务操作
        logger.debug("正在处理...")
        # 模拟异常
        raise ValueError("发生了一个错误")
    except Exception as e:
        logger.error(f"业务逻辑执行过程中出错: {e}")
    finally:
        logger.info("业务逻辑执行结束")


# 调用业务逻辑

# 在项目入口文件中调用
if __name__ == '__main__':
    # 先加载日志配置
    some_business_logic()

    # 然后在项目中使用日志
    logger = logging.getLogger("fileAndConsole")
    logger.debug("这是一个调试日志")
    logger.info("这是一个信息日志")
    logger.error("这是一个错误日志")
