# base_config.py
import os
import yaml
from pathlib import Path
from typing import Any, Dict, Optional


class BaseConfig:
    """配置管理的基类，实现基本的配置加载和访问功能。

    这个基类提供了配置管理的通用功能，可以被其他专门的配置类继承。

    Attributes:
        config (Dict[str, Any]): 存储加载的配置信息的字典
    """

    _instances: Dict[str, 'BaseConfig'] = {}  # 用于存储不同子类的实例

    def __new__(cls) -> 'BaseConfig':
        """实现分类单例模式，每个子类都有自己的唯一实例。

        Returns:
            BaseConfig: 配置类的实例
        """
        if cls not in cls._instances:
            cls._instances[cls.__name__] = super(BaseConfig, cls).__new__(cls)
            cls._instances[cls.__name__].config = {}
        return cls._instances[cls.__name__]

    def _load_config(self, config_name: str) -> None:
        """加载配置文件。

        Args:
            config_name (str): 配置文件的基础名称（不包含扩展名）

        Raises:
            FileNotFoundError: 如果默认配置文件不存在
            yaml.YAMLError: 如果配置文件格式不正确
        """
        try:
            # 确定配置文件路径
            config_dir = Path(__file__).parent.parent.parent / 'config'
            env = os.getenv('APP_ENV', 'dev')
            config_file = config_dir / f'{config_name}-{env}.yml'
            default_config_file = config_dir / f'{config_name}-default.yml'

            # 加载默认配置
            if not default_config_file.exists():
                raise FileNotFoundError(f"默认配置文件不存在: {default_config_file}")

            with default_config_file.open(encoding='utf-8') as f:
                self.config = yaml.safe_load(f) or {}

            # 如果存在环境特定配置，则覆盖默认配置
            if config_file.exists():
                with config_file.open(encoding='utf-8') as f:
                    env_config = yaml.safe_load(f)
                    if env_config:
                        self.config.update(env_config)

        except yaml.YAMLError as e:
            raise yaml.YAMLError(f"配置文件格式错误: {e}")
        except Exception as e:
            raise RuntimeError(f"加载配置文件时发生错误: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值。

        Args:
            key (str): 配置键名
            default (Any, optional): 如果键不存在时返回的默认值

        Returns:
            Any: 配置值或默认值
        """
        return self.config.get(key, default)








# 使用示例
if __name__ == "__main__":
    # 应用配置示例
    app_config = AppConfig()
    database_url = app_config.get('database_url', 'sqlite:///default.db')
    api_key = app_config.get('api_key', 'default_key')

    print("应用配置:")
    print(f"Database URL: {database_url}")
    print(f"API Key: {api_key}")

    # 日志配置示例
    log_config = LogConfig()
    log_level = log_config.get('level', 'INFO')
    log_format = log_config.get('format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler = log_config.get_file_handler_config()

    print("\n日志配置:")
    print(f"Log Level: {log_level}")
    print(f"Log Format: {log_format}")
    print(f"File Handler Config: {file_handler}")

# 配置文件示例:

# config/app-default.yml
"""
database_url: sqlite:///default.db
api_key: default_key
debug: false
"""

# config/app-dev.yml
"""
database_url: sqlite:///dev.db
debug: true
"""

# config/logging.default.yml
"""
level: INFO
format: '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
file_handler:
  filename: app.log
  mode: a
  maxBytes: 10485760  # 10MB
  backupCount: 5
console_handler:
  level: DEBUG
"""

# config/logging.production.yml
"""
level: WARNING
file_handler:
  filename: /var/log/app/app.log
  maxBytes: 52428800  # 50MB
  backupCount: 10
console_handler:
  level: ERROR
"""