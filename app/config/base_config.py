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

        # 确定配置文件路径
        config_dir = Path(__file__).parent.parent.parent / 'config'
        env = os.getenv('APP_ENV', 'dev')
        config_file = config_dir / f'{config_name}-{env}.yml'
        default_config_file = config_dir / f'{config_name}-default.yml'

        try:
            self.config = self._read_yaml(default_config_file)
            if config_file.exists():
                env_config = self._read_yaml(config_file)
                if env_config:
                    self.config.update(env_config)
        except Exception as e:
            raise RuntimeError(f"加载配置文件时发生错误: {e}")

    @staticmethod
    def _read_yaml(file_path: Path) -> Dict[str, Any]:
        """读取 YAML 文件。"""
        if not file_path.exists():
            raise FileNotFoundError(f"配置文件不存在: {file_path}")
        with file_path.open(encoding='utf-8') as f:
            return yaml.safe_load(f) or {}
    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值。

        Args:
            key (str): 配置键名
            default (Any, optional): 如果键不存在时返回的默认值

        Returns:
            Any: 配置值或默认值
        """
        return self.config.get(key, default)