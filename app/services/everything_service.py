
import logging
from typing import Optional

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

    def local_exists_movie(self, serial_number: str):

        # 本地存在的，才叫存在
        # everything检查本地是否存在
        return self.file_exists(serial_number)
    def search_movie(self, serial_number: str, search_path='', file_extensions='') -> Optional[str]:
        return self.everything.search_movie(serial_number, search_path, file_extensions)