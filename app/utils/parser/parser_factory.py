import os
import importlib
import inspect
from app.utils.log_util import debug, info, warning, error, critical
from typing import Dict, Optional, Type, List
from abc import ABC, abstractmethod

from app.utils.parser.base_movie_parser import BaseMovieParser


class ParserFactory:
    """解析器工厂类"""
    _parsers: Dict[str, Type['BaseMovieParser']] = {}
    _initialized = False

    @classmethod
    def initialize(cls, parser_dir: Optional[str] = None) -> None:
        """
        初始化解析器工厂
        Args:
            parser_dir: 解析器目录路径，如果为None则使用默认路径
        """
        if cls._initialized:
            debug("ParserFactory already initialized")
            return

        try:
            if parser_dir is None:
                # 获取当前文件所在目录
                parser_dir = os.path.dirname(os.path.abspath(__file__))

            cls.discover_parsers(parser_dir)
            cls._initialized = True
            info(f"ParserFactory initialized with parsers: {list(cls._parsers.keys())}")
        except Exception as e:
            error(f"Failed to initialize ParserFactory: {e}")
            raise ParserFactoryError(f"Initialization failed: {e}")

    @classmethod
    def discover_parsers(cls, parser_dir: str) -> None:
        """
        自动发现并加载解析器
        Args:
            parser_dir: 解析器目录路径
        """
        debug(f"Discovering parsers in directory: {parser_dir}")

        for file in os.listdir(parser_dir):
            if not file.endswith('_parser.py') or file == 'base_movie_parser.py':
                continue

            module_name = file[:-3]  # 移除.py后缀
            full_module_path = f"app.utils.parser.{module_name}"

            try:
                module = importlib.import_module(full_module_path)
                for name, obj in inspect.getmembers(module):
                    if (inspect.isclass(obj) and
                            issubclass(obj, BaseMovieParser) and
                            obj != BaseMovieParser):
                        source_name = obj.get_source_name()
                        if cls.validate_parser(obj):
                            cls._parsers[source_name] = obj
                            info(f"Successfully registered parser: {name} for source: {source_name}")
                        else:
                            warning(f"Parser validation failed for {name}")
            except Exception as e:
                error(f"Failed to load parser module {module_name}: {e}")

    @classmethod
    def validate_parser(cls, parser_cls: Type['BaseMovieParser']) -> bool:
        """
        验证解析器是否实现了所需的接口
        Args:
            parser_cls: 解析器类
        Returns:
            bool: 是否通过验证
        """
        required_methods = ['parse_movie_details_page', 'parse_search_results']
        return all(hasattr(parser_cls, method) and
                   callable(getattr(parser_cls, method)) for method in required_methods)

    @classmethod
    def register(cls, source_name: str):
        """
        注册解析器的装饰器
        Args:
            source_name: 源名称
        """

        def decorator(parser_cls: Type['BaseMovieParser']):
            if not issubclass(parser_cls, BaseMovieParser):
                raise TypeError(f"{parser_cls.__name__} must inherit from BaseMovieParser")
            if not cls.validate_parser(parser_cls):
                raise TypeError(f"{parser_cls.__name__} missing required methods")

            cls._parsers[source_name] = parser_cls
            info(f"Registered parser {parser_cls.__name__} for source {source_name}")
            return parser_cls

        return decorator

    @classmethod
    def get_parser(cls, source: str = 'javdb') -> Optional['BaseMovieParser']:
        """
        获取解析器实例
        Args:
            source: 源名称
        Returns:
            Optional[BaseMovieParser]: 解析器实例
        """
        if not cls._initialized:
            cls.initialize()

        parser_cls = cls._parsers.get(source)
        if not parser_cls:
            warning(f"Parser not found for source: {source}")
            return None

        try:
            return parser_cls()
        except Exception as e:
            error(f"Failed to instantiate parser for {source}: {e}")
            return None

    @classmethod
    def get_all_parsers(cls) -> Dict[str, Type['BaseMovieParser']]:
        """
        获取所有注册的解析器
        Returns:
            Dict[str, Type[BaseMovieParser]]: 所有注册的解析器
        """
        if not cls._initialized:
            cls.initialize()
        return cls._parsers.copy()

    @classmethod
    def get_available_sources(cls) -> List[str]:
        """
        获取所有可用的解析源
        Returns:
            List[str]: 可用的解析源列表
        """
        if not cls._initialized:
            cls.initialize()
        return list(cls._parsers.keys())


class ParserFactoryError(Exception):
    """解析器工厂相关异常"""
    pass