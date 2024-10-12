import json
from app.utils.redis_client import RedisUtil

class CacheService:
    def __init__(self, redis_client: RedisUtil = None):
        self.redis_client = redis_client if redis_client is not None else RedisUtil()

    def get(self, key: str):
        """从缓存中获取数据"""
        data = self.redis_client.get(key)
        return json.loads(data) if data else None

    def set(self, key: str, value: dict, expire: int = 3600):
        """将数据存入缓存"""
        self.redis_client.setex(key, expire, json.dumps(value))

    def delete(self, key: str):
        """从缓存中删除数据"""
        self.redis_client.delete(key)

    def exists(self, key: str) -> bool:
        """检查键是否存在于缓存中"""
        return self.redis_client.exists(key)

    def add_to_set(self, set_key: str, value: str):
        """将值添加到集合中"""
        self.redis_client.sadd(set_key, value)

    def get_set_members(self, set_key: str) -> list:
        """获取集合中的所有成员"""
        return [member.decode() for member in self.redis_client.smembers(set_key)]