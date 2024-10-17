from dataclasses import dataclass


@dataclass
class MovieSearchResult:
    """
    影片代码和标题
    评分和投票数
    发布日期
    字幕和播放状态
    磁力链接状态
    封面图片URL
    """
    uri: str  # The relative path to the movie detail page
    code: str  # Movie code/number
    title: str  # Movie title
    score: float  # Rating score
    vote_count: int  # Number of votes
    release_date: str  # Release date
    has_subtitles: bool  # Whether the movie has subtitles
    can_play: bool  # Whether the movie is playable
    has_magnet: bool  # Whether the movie has magnet links
    cover_url: str  # URL of the movie cover image
    serial_number: str