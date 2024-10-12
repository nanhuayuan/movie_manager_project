import logging

class LoggingUtil:
    @staticmethod
    def get_logger(logger_name):
        """获取指定名称的日志记录器"""
        logger = logging.getLogger(logger_name)
        if not logger.hasHandlers():
            logger.setLevel(logging.INFO)
            console_handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)
        return logger

    @staticmethod
    def log_info(logger_name, message):
        """记录信息级别日志"""
        logger = LoggingUtil.get_logger(logger_name)
        logger.info(message)

    @staticmethod
    def log_error(logger_name, message):
        """记录错误级别日志"""
        logger = LoggingUtil.get_logger(logger_name)
        logger.error(message)


log = LoggingUtil.get_logger(__name__)