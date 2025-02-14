# app/models/enums.py

from enum import IntEnum


class HaveStatus(IntEnum):
    """
    表示资源（如磁力链接、文件等）的拥有状态。

    这个枚举用于多个字段，如 have_mg, have_file, have_hd, have_sub 等。
    """
    NO = 0  # 没有该资源
    YES = 1  # 拥有该资源
    PENDING = 2  # 资源状态待定或未知





class FavoriteStatus(IntEnum):
    """
    表示收藏状态。

    可用于电影、演员等多种实体的收藏状态标记。
    """
    NOT_FAVORITE = 0  # 未收藏
    FAVORITE = 1  # 已收藏
    OTHER = 2  # 其他状态（如待定、临时收藏等）


class WantedStatus(IntEnum):
    """
    表示用户对某个项目（如电影）的想要程度。
    """
    NOT_WANTED = 0  # 不想要
    WANTED = 1  # 想要
    OTHER = 2  # 其他状态（如考虑中、暂时感兴趣等）


class WatchedStatus(IntEnum):
    """
    表示观看状态。

    主要用于追踪用户是否已经观看了某个电影。
    """
    NOT_WATCHED = 0  # 未观看
    WATCHED = 1  # 已观看
    OTHER = 2  # 其他状态（如部分观看、重复观看等）


class OwnedStatus(IntEnum):
    """
    表示拥有状态。

    用于标记用户是否拥有某个电影的实体拷贝或数字版权。
    """
    NOT_OWNED = 0  # 未拥有
    OWNED = 1  # 已拥有
    OTHER = 2  # 其他状态（如借阅、临时拥有等）


class VisitedStatus(IntEnum):
    """
    表示浏览状态。

    用于记录用户是否访问过某个项目的详情页面或相关信息。
    """
    NOT_VISITED = 0  # 未访问
    VISITED = 1  # 已访问
    OTHER = 2  # 其他状态（如多次访问、最近访问等）


class CommentStatus(IntEnum):
    """
    表示评论状态。

    用于标记某个项目（如电影）是否有评论。
    """
    NO_COMMENTS = 0  # 没有评论
    HAS_COMMENTS = 1  # 有评论
    OTHER = 2  # 其他状态（如评论待审核、仅有内部评论等）


class MagnetSource(IntEnum):
    """
    表示磁力链接的来源。

    用于标记磁力链接是从哪个网站或平台获取的。
    """
    OTHER = 0  # 其他来源或未知来源
    JAVDB = 1  # 来自JavDB
    JAVBUS = 2  # 来自JavBus
    JAVLIB = 3  # 来自JavLibrary
    AVMOO = 4  # 来自Avmoo