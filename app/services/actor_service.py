from dataclasses import dataclass
from typing import Optional

from app.dao import ActorDAO
from app.model.db.movie_model import Actor, Movie
from app.model.enums import DownloadStatus
from app.services.base_service import BaseService
from app.config.log_config import debug, info, warning, error, critical


@dataclass
class ActorService(BaseService[Actor, ActorDAO]):
    def __init__(self):
        super().__init__()
        info("ActorService initialized")

