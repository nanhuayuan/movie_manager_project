from abc import ABC, abstractmethod
from datetime import datetime, date
import re
from typing import List

from app.model.db.movie_model import Movie
from app.utils.parser.model.movie_search_result import MovieSearchResult


class BaseMovieParser(ABC):
    """电影信息解析器基类"""

    @abstractmethod
    def parse_movie_details_page(self, content: str) -> Movie:
        """解析页面内容"""
        pass

    def _safe_extract_text(self, element) -> str:
        """安全提取文本内容"""
        return element.get_text(strip=True) if element else ''

    def _safe_extract_int(self, text: str) -> int:
        """安全提取整数"""
        try:
            return int(re.sub(r'[^0-9]', '', text))
        except (ValueError, TypeError):
            return 0

    def _safe_extract_date(self, text: str) -> date:
        """安全提取日期"""
        try:
            return datetime.strptime(text, '%Y-%m-%d').date()
        except (ValueError, TypeError):
            return date(1970, 1, 1)

    def parse_search_results(self, html_content: str) -> List[MovieSearchResult]:
        """Base method for parsing search results"""
        raise NotImplementedError("Subclasses must implement parse_search_results")