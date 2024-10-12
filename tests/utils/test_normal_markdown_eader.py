import pytest
from pathlib import Path
from unittest.mock import Mock, patch
import unittest
from app.model.db.movie_model import Movie
from app.model.md_file import md_file
from app.utils.read_markdown_file.normal_markdown_reader import NormalMarkdownReader


class TestNormalMarkdownReader(unittest.TestCase):
    @pytest.fixture
    def reader(self):
        return NormalMarkdownReader()

    def test_process_file(self):
        result = NormalMarkdownReader().read_files()

        assert result is not None
        assert len(result.movie_info_list) == 2
        assert result.movie_info_list[0].serial_number == "ABC-123"
        assert result.movie_info_list[1].serial_number == "DEF-456"


if __name__ == '__main__':
    unittest.main()
