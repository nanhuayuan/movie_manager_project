from dataclasses import dataclass
from typing import Optional

from app.dao import GenreDAO
from app.model.db.movie_model import Genre, Movie
from app.model.enums import DownloadStatus
from app.services.base_service import BaseService
from app.utils.log_util import debug, info, warning, error, critical


@dataclass
class GenreService(BaseService[Genre, GenreDAO]):
    def __init__(self):
        super().__init__()
        info("GenreService initialized")

