# database.py
from typing import List, Optional, Tuple, Union
import sqlite3
from contextlib import contextmanager


class Database:
    def __init__(self, database_url: str):
        self.database_url = database_url

    @contextmanager
    def get_connection(self):
        conn = sqlite3.connect(self.database_url)
        try:
            yield conn
        finally:
            conn.close()

    @log_sql(logging.INFO)
    def execute(self, sql: str, params: Optional[Tuple] = None) -> None:
        """执行 SQL 语句"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, params or ())
            conn.commit()

    @log_sql(logging.DEBUG)
    def fetch_one(self, sql: str, params: Optional[Tuple] = None) -> Optional[Tuple]:
        """执行查询并返回一条记录"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, params or ())
            return cursor.fetchone()

    @log_sql(logging.DEBUG)
    def fetch_all(self, sql: str, params: Optional[Tuple] = None) -> List[Tuple]:
        """执行查询并返回所有记录"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, params or ())
            return cursor.fetchall()


# 使用示例
if __name__ == "__main__":
    # 配置数据库日志
    db_log_config = {
        'level': logging.DEBUG,
        'filename': 'sql.log',
        'console_output': True
    }
    setup_db_logger(db_log_config)

    # 使用数据库
    db = Database('example.db')

    # 创建表
    db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT NOT NULL,
            email TEXT
        )
    """)

    # 插入数据
    db.execute(
        "INSERT INTO users (username, email) VALUES (?, ?)",
        ('john_doe', 'john@example.com')
    )

    # 查询数据
    user = db.fetch_one(
        "SELECT * FROM users WHERE username = ?",
        ('john_doe',)
    )
    print(f"Found user: {user}")