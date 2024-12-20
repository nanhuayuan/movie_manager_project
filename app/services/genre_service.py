from dataclasses import dataclass
from typing import Optional

from app.dao import GenreDAO
from app.model.db.movie_model import Genre, Movie
from app.utils.download_client import DownloadStatus
from app.services.base_service import BaseService
from app.config.log_config import debug, info, warning, error, critical


@dataclass
class GenreService(BaseService[Genre, GenreDAO]):
    def __init__(self):
        super().__init__()
        info("GenreService initialized")

