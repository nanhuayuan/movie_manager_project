import unittest

import pytest
from pathlib import Path
from unittest.mock import Mock, patch

from app.model.chart_file_type_enun import ChartFileType
from app.model.db.movie_model import Movie
from app.model.mdfileinfo import MdFileInfo
from app.services.chart_service import ChartService
from app.utils.read_markdown_file.normal_markdown_reader import NormalMarkdownReader
from app.utils.read_markdown_file.top250_markdown_reader import Top250MarkdownReader


class TestChartService(unittest.TestCase):
    @pytest.fixture
    def service(self):
        return ChartService(Path("/test/path"))

    @pytest.fixture
    def mock_normal_reader(self):
        reader = Mock(spec=NormalMarkdownReader)
        reader.read_files.return_value = []
        return reader

    @pytest.fixture
    def mock_top250_reader(self):
        reader = Mock(spec=Top250MarkdownReader)
        reader.read_files.return_value = []
        return reader




if __name__ == '__main__':
    unittest.main()