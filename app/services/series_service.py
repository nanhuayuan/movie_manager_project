from dataclasses import dataclass
from typing import Optional

from app.dao import SeriesDAO
from app.model.db.movie_model import Series, Movie
from app.model.enums import DownloadStatus
from app.services.base_service import BaseService
from app.config.log_config import debug, info, warning, error, critical


@dataclass
class SeriesService(BaseService[Series, SeriesDAO]):
    def __init__(self):
        super().__init__()
        info("SeriesService initialized")

