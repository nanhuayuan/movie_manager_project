# app/utils/db_util.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from contextlib import contextmanager
import threading
from app.config.config_app import AppConfig


class DBUtil:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, db_config=None):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, db_config=None):
        """
        初始化DBUtil，实现单例模式并读取数据库配置

        Args:
            db_config (dict, optional): 数据库配置字典，如果为None则从AppConfig获取
        """
        if hasattr(self, 'engine'):
            return

        if db_config is None:
            self.config_loader = AppConfig()
            db_config = self.config_loader.get_database_config()

        self.database_url = self._construct_db_url(db_config)
        self.echo = db_config.get('echo', False)
        self.pool_size = db_config.get('pool_size', 5)
        self.echo_pool = db_config.get('echo_pool', False)
        self.max_overflow = db_config.get('max_overflow', 10)
        self.pool_recycle = db_config.get('pool_recycle', 3600)
        self.pool_pre_ping = db_config.get('pool_pre_ping', True)

        self.engine = create_engine(
            self.database_url,
            echo=self.echo,
            pool_size=self.pool_size,
            echo_pool=self.echo_pool,
            max_overflow=self.max_overflow,
            pool_recycle=self.pool_recycle,
            pool_pre_ping=self.pool_pre_ping
        )

        session_factory = sessionmaker(bind=self.engine)
        self.Session = scoped_session(session_factory)

    def _construct_db_url(self, db_config):
        """
        构建SQLAlchemy数据库连接URL

        Args:
            db_config (dict): 数据库配置字典

        Returns:
            str: 数据库连接URL
        """
        user = db_config['user']
        password = db_config['password']
        host = db_config['host']
        port = db_config['port']
        dbname = db_config['dbname']
        return f"mysql+pymysql://{user}:{password}@{host}:{port}/{dbname}"

    @contextmanager
    def session_scope(self):
        """
        提供一个自动管理session生命周期的上下文管理器

        Yields:
            Session: 数据库会话对象

        Example:
            with DBUtil().session_scope() as session:
                session.query(User).all()
        """
        session = self.Session()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def get_session(self):
        """
        获取数据库会话

        Returns:
            Session: 线程局部的数据库会话对象

        Note:
            使用此方法时需要手动管理session的生命周期
        """
        return self.Session()

    @property
    def session(self):
        """
        session属性，返回当前线程的数据库会话

        Returns:
            Session: 线程局部的数据库会话对象
        """
        return self.Session()

    def close_sessions(self):
        """清理所有会话"""
        self.Session.remove()

    def close_engine(self):
        """关闭数据库引擎并清理所有会话"""
        self.close_sessions()
        self.engine.dispose()


# 创建全局DBUtil实例
db = DBUtil()