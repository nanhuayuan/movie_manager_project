# test_something.py
import os
import unittest
from app.config.log_config import info, error


class TestYourCode(unittest.TestCase):
    def setUp(self):
        # 设置测试环境标志
        os.environ['TESTING'] = 'true'

    def tearDown(self):
        # 清理环境变量
        os.environ.pop('TESTING', None)

    def test_something(self):
        info("This should appear in console")