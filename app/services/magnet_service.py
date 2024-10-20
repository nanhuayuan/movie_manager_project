from dataclasses import dataclass
from typing import Optional

from app.dao import MagnetDAO
from app.model.db.movie_model import Magnet, Movie
from app.model.enums import DownloadStatus
from app.services.base_service import BaseService
from app.utils.log_util import debug, info, warning, error, critical


@dataclass
class MagnetService(BaseService[Magnet, MagnetDAO]):
    def __init__(self):
        super().__init__()
        info("MagnetService initialized")

