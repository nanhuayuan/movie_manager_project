import pytest
from pathlib import Path
from unittest.mock import Mock, patch
import unittest
from app.model.db.movie_model import Movie
from app.model.mdfileinfo import MdFileInfo
from app.utils.parser.javdb_parser import JavdbParser
from app.utils.parser.parser_factory import ParserFactory
from app.utils.read_markdown_file.normal_markdown_reader import NormalMarkdownReader


class TestJavdbParser(unittest.TestCase):
    @pytest.fixture
    def reader(self):
        return JavdbParser()

    def test_parse_movie_details_page(self):
        # 获取所有注册的解析器
        all_parsers = ParserFactory.get_all_parsers()
        print("Registered parsers:", list(all_parsers.keys()))

        # 使用特定解析器
        parser = ParserFactory.get_parser('javdb')
        if parser:
            path = "D:/同步_临时/电影库/NSFS-039-page-2.txt"
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            movie_info = parser.parse_movie_details_page(content)
            print(movie_info)
    def test_parse_search_results(self):
        # 获取所有注册的解析器
        all_parsers = ParserFactory.get_all_parsers()
        print("Registered parsers:", list(all_parsers.keys()))

        # 使用特定解析器
        parser = ParserFactory.get_parser('javdb')
        if parser:
            path = "D:/同步_临时/电影库/NSFS-039-search-精简1.txt"
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            movie_info = parser.parse_search_results(content)
            print(movie_info)

if __name__ == '__main__':
    unittest.main()
