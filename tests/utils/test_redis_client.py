import unittest
import json
from unittest.mock import MagicMock
from app.utils.redis_client import RedisUtil


class TestRedisClient(unittest.TestCase):
    def setUp(self):
        # 假设AppConfig的REDIS_HOST和REDIS_PORT已经正确设置
        self.redis_client = RedisUtil()
        # Mock redis对象
        self.redis_client.redis = MagicMock()

    def test_set_value_with_dict(self):
        # 测试使用字典作为value
        key = 'test_key'
        value = {'test': 'value'}
        expiration = 100

        self.redis_client.set_value(key, value, expiration)

        # 验证是否正确地将字典转换为JSON字符串并设置到Redis
        self.redis_client.redis.set.assert_called_with(key, json.dumps(value), ex=expiration)

    def test_set_value_with_string(self):
        # 测试使用字符串作为value
        key = 'test_key'
        value = 'test_value'
        expiration = None

        self.redis_client.set_value(key, value, expiration)

        # 验证是否正确地将字符串设置到Redis
        self.redis_client.redis.set.assert_called_with(key, value, ex=expiration)

    def test_set_value_with_expiration(self):
        # 测试设置带有过期时间的键值对
        key = 'test_key'
        value = 'test_value'
        expiration = 100

        self.redis_client.set_value(key, value, expiration)

        # 验证是否正确地设置了过期时间
        self.redis_client.redis.set.assert_called_with(key, value, ex=expiration)

    def test_set_value_without_expiration(self):
        # 测试设置不带有过期时间的键值对
        key = 'test_key'
        value = 'test_value'
        expiration = None

        self.redis_client.set_value(key, value, expiration)

        # 验证是否正确地设置了键值对，且没有过期时间
        self.redis_client.redis.set.assert_called_with(key, value, ex=expiration)

    def test_get_value_json(self):
        # 测试能正常解析JSON的情况
        self.redis_client.redis = MagicMock()
        self.redis_client.redis.get.return_value = '{"key": "value"}'

        result = self.redis_client.get_value('test_key')
        self.assertEqual(result, {'key': 'value'})

    def test_get_value_non_json(self):
        # 测试不能解析为JSON的情况
        self.redis_client.redis = MagicMock()
        self.redis_client.redis.get.return_value = 'non-JSON-value'

        result = self.redis_client.get_value('test_key')
        self.assertEqual(result, 'non-JSON-value')

    def test_get_value_none(self):
        # 测试Redis中键不存在的情况
        self.redis_client.redis = MagicMock()
        self.redis_client.redis.get.return_value = None

        result = self.redis_client.get_value('non_existent_key')
        self.assertIsNone(result)

    def test_get_value_invalid_json(self):
        # 测试Redis返回的值是无效JSON的情况
        self.redis_client.redis = MagicMock()
        self.redis_client.redis.get.return_value = '{invalid JSON}'

        result = self.redis_client.get_value('test_key')
        self.assertEqual(result, '{invalid JSON}')

    def test_delete_key(self):
        # 测试数据
        key_to_delete = 'test_key'

        # 调用待测试的方法
        self.redis_client.delete_key(key_to_delete)

        # 验证预期结果
        # 验证是否调用了redis的delete方法
        self.redis_client.redis.delete.assert_called_once_with(key_to_delete)

    def test_key_exists(self):
        # 测试键存在的情况
        self.redis_client.redis.exists.return_value = True
        self.assertTrue(self.redis_client.key_exists('test_key'))

        # 测试键不存在的情况
        self.redis_client.redis.exists.return_value = False
        self.assertFalse(self.redis_client.key_exists('nonexistent_key'))

    def tearDown(self):
        self.redis_client = None


if __name__ == '__main__':
    unittest.main()
