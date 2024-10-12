
import logging

from app.utils import EverythingUtils


class EverythingService:
    def __init__(self,):
        self.everything = EverythingUtils()
        self.logger = logging.getLogger(__name__)

    def file_exists(self, movie_title: str) -> bool:
        try:
            results = self.everything.search_movie(movie_title)
            return len(results) > 0
        except Exception as e:
            self.logger.error(f"Error searching Everything for movie {movie_title}: {str(e)}")
            return False