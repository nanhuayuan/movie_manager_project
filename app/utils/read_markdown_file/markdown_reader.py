from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Optional, Protocol
import logging
from concurrent.futures import ThreadPoolExecutor
import threading

from app.config.app_config import AppConfig
from app.model.md_file import md_file

# 配置日志记录器
logger = logging.getLogger(__name__)


class MarkdownReader(ABC):
    """
    Markdown 读取器抽象基类
    """

    def __init__(self):
        self.exclude_files = {"success.md"}
        self._cache = {}
        self._cache_lock = threading.Lock()
        self.config = AppConfig().get_md_file_path_config()

    def get_base_path(self, base_path: Path) -> List[md_file]:

        if base_path is None:
            return Path(Path(__file__).parent.parent.parent.parent / self.config['movie_list_path'])

        return base_path



    @abstractmethod
    def process_file(self, file_path: Path = None) -> Optional[md_file]:
        """处理单个文件的抽象方法"""
        pass

    def read_files(self, base_path: Path = None) -> List[md_file]:
        """
        读取目录下的所有有效 Markdown 文件

        Args:
            base_path: 文件目录路径

        Returns:
            List[md_file]: 包含电影信息的 md_file 列表
        """

        base_path = self.get_base_path(base_path)
        try:
            valid_files = [
                f for f in base_path.glob("*.md")
                if f.name not in self.exclude_files
            ]

            results = []
            with ThreadPoolExecutor() as executor:
                future_to_file = {
                    executor.submit(self.process_file, f): f
                    for f in valid_files
                }

                for future in future_to_file:
                    result = future.result()
                    if result:
                        results.append(result)

            return results
        except Exception as e:
            logger.error(f"读取文件时发生错误: {e}")
            return []

    def _get_cached_result(self, file_path: Path) -> Optional[md_file]:
        """获取缓存的处理结果"""
        with self._cache_lock:
            cache_key = str(file_path)
            if cache_key in self._cache:
                return self._cache[cache_key]
        return None

    def _cache_result(self, file_path: Path, result: md_file):
        """缓存处理结果"""
        with self._cache_lock:
            self._cache[str(file_path)] = result
