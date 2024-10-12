from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Protocol
import re
import logging
from concurrent.futures import ThreadPoolExecutor
import threading

from app.model.db.movie_model import Movie
from app.model.md_file import md_file

# 配置日志记录器
from app.utils.read_markdown_file.markdown_reader import MarkdownReader

logger = logging.getLogger(__name__)


class Top250MarkdownReader(MarkdownReader):
    """TOP 250 榜单 Markdown 读取器"""

    RANKING_PREFIX = "Ranking: "
    TAG_PREFIX = "Tag: "
    URI_PATTERN = re.compile(r'\(https://javdb521\.com(.+?)\)')

    def process_file(self, file_path: Path = None) -> Optional[md_file]:
        """
        处理 TOP 250 榜单文件

        Args:
            file_path: 文件路径

        Returns:
            Optional[md_file]: 处理后的 md_file 对象，失败返回 None
        """
        # 检查缓存
        cached_result = self._get_cached_result(file_path)
        if cached_result:
            return cached_result

        try:
            md_file_obj = md_file()
            md_file_obj.file_name = file_path.name
            md_file_obj.file_path = str(file_path)
            md_file_obj.movie_info_list = []
            md_file_obj.code_list = []

            current_movie = None
            with file_path.open('r', encoding='utf-8') as f:
                for line in f:
                    current_movie = self._process_line(
                        line.strip(), current_movie, md_file_obj
                    )

            # 缓存结果
            self._cache_result(file_path, md_file_obj)
            return md_file_obj
        except Exception as e:
            logger.error(f"处理文件 {file_path} 时发生错误: {e}")
            return None

    def _process_line(self, line: str, current_movie: Optional[Movie],
                      md_file_obj: md_file) -> Optional[Movie]:
        """
        处理单行内容

        Args:
            line: 行内容
            current_movie: 当前处理的电影对象
            md_file_obj: 当前的 md_file 对象

        Returns:
            Optional[Movie]: 更新后的当前电影对象
        """
        if line.startswith(self.RANKING_PREFIX):
            current_movie = Movie()
            current_movie.ranking = int(self._extract_value(line, self.RANKING_PREFIX))
            current_movie.magnet = []
        elif line.startswith(self.TAG_PREFIX) and current_movie:
            code = self._extract_value(line, self.TAG_PREFIX)
            current_movie.serial_number = code
            md_file_obj.code_list.append(code)
        else:
            uri_match = self.URI_PATTERN.search(line)
            if uri_match and current_movie:
                current_movie.uri = uri_match.group(1)
                md_file_obj.movie_info_list.append(current_movie)
                current_movie = None
        return current_movie

    @staticmethod
    def _extract_value(line: str, prefix: str) -> str:
        """从行中提取值"""
        return line[len(prefix):].replace("<br>", "").strip()
