from dataclasses import dataclass
from typing import Optional

from app.dao import DownloadFailureDAO
from app.model.db.movie_model import DownloadFailure, Movie
from app.utils.download_client import DownloadStatus
from app.services.base_service import BaseService
from app.config.log_config import debug, info, warning, error, critical


@dataclass
class DownloadFailureService(BaseService[DownloadFailure, DownloadFailureDAO]):
    def __init__(self):
        super().__init__()
        info("DownloadFailureService initialized")

    def add_download_failed(self, movie: Movie,) -> Optional[DownloadFailure]:
        try:
            info(f"添加到下载失败表: {movie.serial_number}")
            download_failure = DownloadFailure(
                movie_id=movie.id,
                magnet_xt=movie.magnets[0].magnet_xt,
                censored_id=movie.censored_id,
                magnet_id=movie.magnets[0].id,
            )
            return self.create(download_failure)
        except Exception as e:
            error(f"添加到下载失败表失败：{e}")