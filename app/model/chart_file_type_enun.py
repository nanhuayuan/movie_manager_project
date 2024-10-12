from enum import Enum
import logging

logger = logging.getLogger(__name__)


class ChartFileType(Enum):
    """
    电影榜单类型枚举

    Attributes:
        NORMAL: 普通榜单
        TOP_250: TOP 250 榜单
    """
    NORMAL = "normal"
    TOP_250 = "top_250"
