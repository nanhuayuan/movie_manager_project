import redis
import json
from app.config.app_config import AppConfig


class RedisUtil:
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

            cls._instance.redis = redis.Redis(
                host=redis_url,
                port=port,
                db=db,
                password=password,
                decode_responses=True
            )

        return cls._instance

    def set_value(self, key, value, expiration=None):
        """设置键值对到 Redis，支持可选过期时间"""
        if isinstance(value, dict):
            value = json.dumps(value)
        self.redis.set(key, value, ex=expiration)

    def get_value(self, key):
        """从 Redis 获取键对应的值"""
        value = self.redis.get(key)
        try:
            return json.loads(value)
        except (TypeError, json.JSONDecodeError):
            return value

    def delete_key(self, key):
        """从 Redis 删除一个键"""
        self.redis.delete(key)

    def key_exists(self, key):
        """检查键是否存在"""
        return self.redis.exists(key)
