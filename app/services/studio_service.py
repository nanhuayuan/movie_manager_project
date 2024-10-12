import logging

from app.dao import StudioDAO


class StudioService:
    def __init__(self, studio_dao: StudioDAO = None):
        self.studio_dao = studio_dao if studio_dao is not None else StudioDAO()
        self.logger = logging.getLogger(__name__)