import json
import redis

from app.config.app_config import AppConfig
from app.utils.redis_client import RedisUtil

class CacheService:
    _instance = None

    def __new__(cls):
        """
        该函数实现单例模式，确保类仅有一个实例。首次调用时：
        1.通过super().__new__(cls)创建实例；
        2.初始化DBUtil，加载数据库配置；
        3.从配置中获取Redis数据库连接信息；
        4.使用这些信息创建Redis客户端对象并存储在类属性_instance.client中。 之后的调用直接返回已有实例。
        """
        if cls._instance is None:
            cls._instance = super().__new__(cls)

            """初始化DBUtil，读取数据库配置"""
            config_loader = AppConfig()
            redis_config = config_loader.get_redis_config()

            # 从配置文件中获取数据库连接URL
            redis_url = redis_config.get('host', '127.0.0.1')
            port = redis_config.get('port', 6379)
            db = redis_config.get('db', 0)
            password = redis_config.get('password', '')

            cls._instance.redis_client = redis.Redis(
                host=redis_url,
                port=port,
                db=db,
                password=password,
                decode_responses=True
            )

        return cls._instance

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