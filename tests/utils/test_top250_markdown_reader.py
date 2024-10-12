import pytest
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from app.model.db.movie_model import Movie
from app.model.md_file import md_file
from app.utils.read_markdown_file.top250_markdown_reader import Top250MarkdownReader


class TestTop250MarkdownReader(unittest.TestCase):
    @pytest.fixture
    def reader(self):
        return Top250MarkdownReader()

    def test_process_file(self):

        reader = Top250MarkdownReader()
        tmp_path = Path("d:/")
        test_file = tmp_path / "test.md"
        test_file.write_text("""
Ranking: 1
Tag: ABC-123
(https://javdb521.com/movies/abc123)
        """.strip())

        result = reader.process_file(test_file)

        assert result is not None
        assert len(result.movie_info_list) == 1
        assert result.movie_info_list[0].ranking == "1"
        assert result.movie_info_list[0].serial_number == "ABC-123"
        assert result.movie_info_list[0].uri == "/movies/abc123"

    def test_read_files(self):
        result = Top250MarkdownReader().read_files()

        assert result is not None
        assert len(result.movie_info_list) == 2
        assert result.movie_info_list[0].serial_number == "ABC-123"
        assert result.movie_info_list[1].serial_number == "DEF-456"



if __name__ == '__main__':
    unittest.main()