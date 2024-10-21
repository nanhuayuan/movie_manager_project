from dataclasses import dataclass
from typing import Optional

from app.dao import StudioDAO
from app.model.db.movie_model import Studio, Movie
from app.model.enums import DownloadStatus
from app.services.base_service import BaseService
from app.config.log_config import debug, info, warning, error, critical


@dataclass
class StudioService(BaseService[Studio, StudioDAO]):
    def __init__(self):
        super().__init__()
        info("StudioService initialized")

