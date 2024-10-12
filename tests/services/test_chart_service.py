import unittest

import pytest
from pathlib import Path
from unittest.mock import Mock, patch

from app.model.chart_file_type_enun import ChartFileType
from app.model.db.movie_model import Movie
from app.model.md_file import md_file
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

    def test_get_movie_chart_normal(self, service, mock_normal_reader):
        service.readers[ChartFileType.NORMAL] = mock_normal_reader

        result = service.get_movie_chart(ChartFileType.NORMAL)

        assert result == []
        mock_normal_reader.read_files.assert_called_once_with(service.base_path)

    def test_get_movie_chart_top250(self, service, mock_top250_reader):
        service.readers[ChartFileType.TOP_250] = mock_top250_reader

        result = service.get_movie_chart(ChartFileType.TOP_250)

        assert result == []
        mock_top250_reader.read_files.assert_called_once_with(service.base_path)

    def test_get_movie_chart_invalid_type(self, service):
        with pytest.raises(ValueError):
            service.get_movie_chart("invalid_type")

    def test_register_reader(self, service, mock_normal_reader):
        service.register_reader(ChartFileType.TEST, mock_normal_reader)

        assert service.readers[ChartFileType.TEST] == mock_normal_reader



if __name__ == '__main__':
    unittest.main()