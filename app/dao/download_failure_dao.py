# app/dao/download_failure_dao.py
from typing import List, Optional, Dict, Any
from sqlalchemy import desc, or_
from datetime import datetime

from .base_dao import BaseDAO
from app.model.db.movie_model import DownloadFailure
from app.config.log_config import debug, info, warning, error, critical


class DownloadFailureDAO(BaseDAO[DownloadFailure]):
    def __init__(self):
        super().__init__()