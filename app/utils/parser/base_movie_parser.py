from abc import ABC, abstractmethod
from datetime import datetime, date
from typing import List, Any, Dict
import re
from app.config.log_config import debug, info, warning, error, critical
from bs4 import BeautifulSoup

from app.model.db.movie_model import Movie
from app.utils.parser.model.movie_search_result import MovieSearchResult


class ParserError(Exception):
    """解析器相关异常"""
    pass


class BaseMovieParser(ABC):
    """电影信息解析器基类"""

    @classmethod
    def get_source_name(cls) -> str:
        """获取解析器源名称"""
        return cls.__name__.lower().replace('parser', '')

    @abstractmethod
    def parse_movie_details_page(self, soup: BeautifulSoup) -> Movie:
        """
        解析电影详情页面
        Args:
            soup: 页面内容
        Returns:
            Movie: 电影信息对象
        """
        pass

    @abstractmethod
    def parse_search_results(self, soup: BeautifulSoup) -> List[MovieSearchResult]:
        """
        解析搜索结果页面
        Args:
            soup: 页面内容
        Returns:
            List[MovieSearchResult]: 搜索结果列表
        """
        pass

    @abstractmethod
    def parse_actor_search_results(self, html_content):
        """
        解析演员搜索结果页面
        返回演员列表，每个演员包含名称、URI和照片链接
        """
        pass

    @abstractmethod
    def parse_actor_page_info(self, html_content):
        """
        解析演员页面信息，获取电影数量和最大页数
        返回 (电影数量, 最大页数)
        """
        pass

    @abstractmethod
    def parse_actor_movies_page(self, html_content, min_evaluations=200):
        """
        解析演员电影页面，返回符合条件的电影列表
        """
        pass


    def supports_feature(self, feature_name: str) -> bool:
        """
        检查是否支持特定功能
        Args:
            feature_name: 功能名称
        Returns:
            bool: 是否支持该功能
        """
        return hasattr(self, feature_name) and callable(getattr(self, feature_name))

    def _safe_extract_text(self, element: Any) -> str:
        """
        安全提取文本内容
        Args:
            element: BeautifulSoup元素
        Returns:
            str: 提取的文本
        """
        try:
            return element.get_text(strip=True) if element else ''
        except Exception as e:
            warning(f"Failed to extract text from element: {e}")
            return ''

    def _safe_extract_int(self, text: str) -> int:
        """
        安全提取整数
        Args:
            text: 待提取的文本
        Returns:
            int: 提取的整数
        """
        try:
            return int(re.sub(r'[^0-9]', '', text))
        except (ValueError, TypeError) as e:
            warning(f"Failed to extract int from text '{text}': {e}")
            return 0

    def _safe_extract_date(self, text: str) -> date:
        """
        安全提取日期
        Args:
            text: 待提取的文本
        Returns:
            date: 提取的日期
        """
        try:
            return datetime.strptime(text, '%Y-%m-%d').date()
        except (ValueError, TypeError) as e:
            warning(f"Failed to extract date from text '{text}': {e}")
            return date(1970, 1, 1)

    def parse_with_retry(self, func: callable, *args, max_retries: int = 3, **kwargs) -> Any:
        """
        带重试机制的解析方法
        Args:
            func: 要执行的函数
            max_retries: 最大重试次数
            *args: 位置参数
            **kwargs: 关键字参数
        Returns:
            Any: 函数返回值
        """
        last_error = None
        for attempt in range(max_retries):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_error = e
                warning(f"Parse attempt {attempt + 1} failed: {e}")

        raise ParserError(f"All {max_retries} parse attempts failed. Last error: {last_error}")