import markdown
import re
import redis
from sqlalchemy.orm import Session


class MovieListProcessor:
    def __init__(self, db_session: Session, redis_client: redis.Redis):
        self.db = db_session
        self.redis = redis_client

    def parse_markdown(self, file_path: str):
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 使用正则表达式提取电影的序列号（例如：ABP-123）
        movie_serials = re.findall(r'[A-Z]{2,}-\d{2,}', content)
        return movie_serials

    def check_movie_in_db(self, serial_number: str):
        # 检查 Redis 缓存中是否有此电影
        if self.redis.exists(serial_number):
            return True

        # 如果缓存中不存在，则查询数据库
        result = self.db.execute("SELECT id FROM movie WHERE serial_number = :serial_number",
                                 {'serial_number': serial_number}).fetchone()
        if result:
            # 如果电影存在，将其缓存到 Redis
            self.redis.set(serial_number, result['id'])
            return True
        return False

    def process_movie_list(self, file_path: str):
        movie_serials = self.parse_markdown(file_path)
        for serial in movie_serials:
            if not self.check_movie_in_db(serial):
                print(f"电影 {serial} 不在数据库中")
                # 调用抓取功能，或记录缺失数据
            else:
                print(f"电影 {serial} 已存在")
