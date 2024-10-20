from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Protocol
import re
import logging
from concurrent.futures import ThreadPoolExecutor
import threading

from app.model.db.movie_model import Movie, ChartEntry
from app.model.db.movie_model import Chart

# 配置日志记录器
from app.utils.read_markdown_file.markdown_reader import MarkdownReader

logger = logging.getLogger(__name__)


class Top250MarkdownReader(MarkdownReader):
    """TOP 250 榜单 Markdown 读取器"""

    RANKING_PREFIX = "Ranking: "
    TAG_PREFIX = "Tag: "
    URI_PATTERN = re.compile(r'\(https://javdb521\.com(.+?)\)')

    def process_file(self, file_path: Path = None) -> Optional[Chart]:
        """
        处理 TOP 250 榜单文件

        Args:
            file_path: 文件路径

        Returns:
            Optional[Chart]: 处理后的 md_file 对象，失败返回 None
        """
        # 检查缓存
        cached_result = self._get_cached_result(file_path)
        if cached_result:
            return cached_result

        try:
            chart_obj = Chart()
            chart_obj.name = file_path.name.split('.')[0]
            chart_obj.file_path = str(file_path)
            chart_obj.entries = []
            chart_obj.code_list = []

            current_chart_entry = None
            with file_path.open('r', encoding='utf-8') as f:
                for line in f:
                    current_chart_entry = self._process_line(
                        line.strip(), current_chart_entry, chart_obj
                    )

            # 缓存结果
            self._cache_result(file_path, chart_obj)
            return chart_obj
        except Exception as e:
            logger.error(f"处理文件 {file_path} 时发生错误: {e}")
            return None

    def _process_line(self, line: str, current_chart_entry: Optional[ChartEntry],
                      chart_obj: Chart) -> Optional[ChartEntry]:
        """
        处理单行内容

        Args:
            line: 行内容
            current_chart_entry: 当前处理的电影对象
            chart_obj: 当前的 md_file 对象

        Returns:
            Optional[ChartEntry]: 更新后的当前电影对象
        """
        if line.startswith(self.RANKING_PREFIX):
            current_chart_entry = ChartEntry()
            current_chart_entry.rank = int(self._extract_value(line, self.RANKING_PREFIX))
            current_chart_entry.magnet = []
        elif line.startswith(self.TAG_PREFIX) and current_chart_entry:
            code = self._extract_value(line, self.TAG_PREFIX)
            current_chart_entry.serial_number = code
            chart_obj.code_list.append(code)
        else:
            uri_match = self.URI_PATTERN.search(line)
            if uri_match and current_chart_entry:
                current_chart_entry.link = uri_match.group(1)
                chart_obj.entries.append(current_chart_entry)
                current_chart_entry = None
        return current_chart_entry

    @staticmethod
    def _extract_value(line: str, prefix: str) -> str:
        """从行中提取值"""
        return line[len(prefix):].replace("<br>", "").strip()
