
from typing import List, Optional, Type, Dict



class ParserFactory:
    """解析器工厂类"""

    _parsers: Dict[str, Type['BaseMovieParser']] = {}

    @classmethod
    def register(cls, source_name: str):
        """注册解析器的装饰器"""

        def decorator(parser_cls: Type['BaseMovieParser']):
            cls._parsers[source_name] = parser_cls
            return parser_cls

        return decorator

    @classmethod
    def get_parser(cls, source: str = 'javdb') -> Optional['BaseMovieParser']:
        """获取解析器实例"""
        parser_cls = cls._parsers.get(source)
        return parser_cls() if parser_cls else None

    @classmethod
    def get_all_parsers(cls) -> Dict[str, Type['BaseMovieParser']]:
        """获取所有注册的解析器"""
        return cls._parsers