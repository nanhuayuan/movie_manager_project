# conftest.py
import os
import pytest


# 或者在 pytest 的 conftest.py

@pytest.fixture(autouse=True)
def setup_testing_environment():
    os.environ['TESTING'] = 'true'
    yield
    os.environ.pop('TESTING', None)
