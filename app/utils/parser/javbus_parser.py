from typing import List

from app.model.db.movie_model import Movie
from app.utils.parser.base_movie_parser import BaseMovieParser
from app.utils.parser.model.movie_search_result import MovieSearchResult
from app.utils.parser.parser_factory import ParserFactory


@ParserFactory.register('javbus')
class JavbusParser(BaseMovieParser):
    """JavBus网站解析器"""

    def parse_movie_details_page(self, content: str) -> Movie:
        # TODO: 实现JavBus网站的解析逻辑
        return Movie()


    #-------------------------parse_search_results ----start------------------------------------------
    def parse_search_results(self, html_content: str) -> List[MovieSearchResult]:
        # Implementation for JavbusParser would go here
        # Following similar pattern but with different selectors
        pass

    #-------------------------parse_search_results ----end-----------------------------------------