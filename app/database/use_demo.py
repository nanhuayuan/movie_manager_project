# myproject/main.py
from app.config.config_log import LogConfig
from app.config.config_app import AppConfig
from app.database.db_logger import setup_db_logger
from app.database.database import Database


def main():
    # 加载配置
    log_config = LogConfig()
    app_config = AppConfig()

    # 设置数据库日志
    db_log_config = log_config.get_db_log_config()
    setup_db_logger(db_log_config)

    # 初始化数据库连接
    db = Database(app_config.get('database', {}).get('url', 'default.db'))

    try:
        # 执行一些数据库操作
        db.execute(
            "INSERT INTO users (username, email) VALUES (?, ?)",
            ('alice', 'alice@example.com')
        )

        users = db.fetch_all("SELECT * FROM users")
        print(f"Found {len(users)} users")

    except Exception as e:
        logging.error(f"Database operation failed: {e}")


if __name__ == "__main__":
    main()