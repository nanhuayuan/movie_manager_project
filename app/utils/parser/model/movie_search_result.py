from dataclasses import dataclass
from app.config.log_config import debug, info, warning, error, critical

@dataclass
class MovieSearchResult:
    """
    表示影片搜索结果的数据类。

    属性:
        uri (str): 电影详情页的相对路径，用于指向电影的具体信息页面。
        code (str): 电影代码/编号，例如 "aaa-123"。
        title (str): 电影的标题。
        score (float): 电影的评分，通常是一个介于0到10之间的小数。
        vote_count (int): 投票数，表示为该电影评分的总人数。
        release_date (str): 电影的发布日期，格式通常为 "YYYY-MM-DD"。
        has_subtitles (bool): 是否有字幕，True表示有字幕，False表示无字幕。
        can_play (bool): 是否可以播放，True表示电影可播放，False表示不可播放。
        has_magnet (bool): 是否有磁力链接，True表示有可用的磁力链接，False表示无可用链接。
        cover_url (str): 电影封面图片的URL地址。
        serial_number (str): 电影的序列号，通常用于标识系列中的某一部电影。
    """

    uri: str  # 电影详情页的相对路径
    code: str  # 电影代码/编号
    title: str  # 电影标题
    score: float  # 评分
    vote_count: int  # 投票数
    release_date: str  # 发布日期
    has_subtitles: bool  # 是否有字幕
    can_play: bool  # 是否可以播放
    has_magnet: bool  # 是否有磁力链接
    cover_url: str  # 封面图片的URL
    serial_number: str  # 序列号

    def __post_init__(self):
        """
        数据类的初始化后处理方法，用于验证和调整属性。

        如果某些属性值不符合预期格式，可以在这里进行调整或抛出异常。
        """
        # 验证评分范围是否在0到10之间
        if not (0.0 <= self.score <= 10.0):
            raise ValueError(f"评分必须在0到10之间，当前值: {self.score}")

        # 验证投票数是否为非负整数
        if self.vote_count < 0:
            raise ValueError(f"投票数不能为负数，当前值: {self.vote_count}")

        # 检查发布日期是否为空
        if not self.release_date:
            raise ValueError("发布日期不能为空")

        # 检查封面图片URL是否为非空字符串
        if not self.cover_url:
            raise ValueError("封面图片的URL不能为空")

        # 日志记录初始化成功
        debug(f"MovieSearchResult对象初始化成功: {self}")
