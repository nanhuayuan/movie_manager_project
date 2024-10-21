class DownloadStatus:
    def __init__(self, size: int = 0, dlspeed: int = 0, hash: str = "", magnet_uri: str = "", progress: float = 0.0):
        """
        DownloadStatus Bean 类，表示下载状态的相关信息。

        :param size: 种子对应内容的大小 (单位: B)
        :param dlspeed: 种子的当前下载速度 (单位: B/s)
        :param hash: 种子的 hash 值，即 magnet:?xt=urn:btih: 后面的值
        :param magnet_uri: 种子的完整 magnet 链接
        :param progress: 种子当前的下载进度 (范围 0.0 到 1.0，表示百分比)
        """
        self.size = size
        self.dlspeed = dlspeed
        self.hash = hash
        self.magnet_uri = magnet_uri
        self.progress = progress

    def __repr__(self):
        return (f"DownloadStatus(size={self.size}, dlspeed={self.dlspeed}, hash='{self.hash}', "
                f"magnet_uri='{self.magnet_uri}', progress={self.progress})")
