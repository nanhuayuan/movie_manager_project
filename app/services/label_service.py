from dataclasses import dataclass
from typing import Optional

from app.dao import LabelDAO
from app.model.db.movie_model import Label, Movie
from app.utils.download_client import DownloadStatus
from app.services.base_service import BaseService
from app.config.log_config import debug, info, warning, error, critical


@dataclass
class LabelService(BaseService[Label, LabelDAO]):
    def __init__(self):
        super().__init__()
        info("LabelService initialized")

