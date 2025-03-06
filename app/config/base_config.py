# base_config.py
import os
import yaml
from pathlib import Path
from typing import Any, Dict


class BaseConfig:
    _instances: Dict[str, 'BaseConfig'] = {}

    def __new__(cls) -> 'BaseConfig':
        if cls not in cls._instances:
            cls._instances[cls.__name__] = super(BaseConfig, cls).__new__(cls)
            cls._instances[cls.__name__].config = {}
        return cls._instances[cls.__name__]

    def _load_config(self, config_name: str) -> None:
        config_dir = Path(__file__).parent.parent.parent / 'config'
        env = os.getenv('APP_ENV', 'test')

        base_config = self._read_yaml(config_dir / f'{config_name}-base.yml')
        env_config = self._read_yaml(config_dir / f'{config_name}-{env}.yml')

        # 使用深度合并
        self.config = self._deep_merge(base_config, env_config)

    def _deep_merge(self, base: Dict, override: Dict) -> Dict:
        """递归合并两个字典,保留基础配置的结构"""
        result = base.copy()

        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value

        return result

    @staticmethod
    def _read_yaml(file_path: Path) -> Dict[str, Any]:
        with file_path.open(encoding='utf-8') as f:
            return yaml.safe_load(f) or {}

    def get(self, key: str, default: Any = None) -> Any:
        return self.config.get(key, default)