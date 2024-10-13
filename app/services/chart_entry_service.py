from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Protocol
import re
import logging
from concurrent.futures import ThreadPoolExecutor
import threading

from app.config.app_config import AppConfig
from app.dao import ChartEntryDAO, ChartEntryDAO
from app.model.chart_file_type_enun import ChartFileType
from app.model.db.movie_model import Movie, ChartEntry
from app.model.md_file import md_file

# 配置日志记录器
from app.utils.db_util import db
from app.utils.read_markdown_file.markdown_reader import MarkdownReader
from app.utils.read_markdown_file.normal_markdown_reader import NormalMarkdownReader
from app.utils.read_markdown_file.top250_markdown_reader import Top250MarkdownReader

logger = logging.getLogger(__name__)

@dataclass
class ChartEntryService:


    def __init__(self):
        self.chart_entry_dao = ChartEntryDAO()


    def get_by_movie_id_or_create(self, chart_entry: ChartEntry = None) -> Optional[ChartEntry]:
        """
        根据名称获取榜单类型，如果不存在则创建一个新的
        """

        if not isinstance(chart_entry, ChartEntry):
            raise ValueError("chart_entry must be an instance of ChartEntry")

        try:
            flg = self.chart_entry_dao.get_by_movie_id(chart_entry.movie_id)
            if flg is None:
                return self.chart_entry_dao.create(chart_entry)
            else:
                return flg
        except Exception as e:
            # 处理异常
            print(f"An error occurred: {e}")
            return None

