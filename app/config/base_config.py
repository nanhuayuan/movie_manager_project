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
        env = os.getenv('APP_ENV', 'dev')

        base_config = self._read_yaml(config_dir / f'{config_name}-base.yml')
        env_config = self._read_yaml(config_dir / f'{config_name}-{env}.yml')

        self.config = base_config
        self.config.update(env_config)

    @staticmethod
    def _read_yaml(file_path: Path) -> Dict[str, Any]:
        with file_path.open(encoding='utf-8') as f:
            return yaml.safe_load(f) or {}

    def get(self, key: str, default: Any = None) -> Any:
        return self.config.get(key, default)