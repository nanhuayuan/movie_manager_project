import qbittorrentapi

def download_torrent(magnet_link, qb_client):
    """使用 qbittorrent 下载磁力链接"""
    try:
        qb_client.torrents_add(urls=magnet_link)
        return True
    except Exception as e:
        print(f"下载磁力链接时出错: {e}")
        return False

def check_download_status(qb_client, torrent_hash):
    """检查下载的状态，返回进度和状态信息"""
    torrent = qb_client.torrents_info(torrent_hash=torrent_hash)
    if torrent:
        return torrent[0].progress, torrent[0].state
    return None, None
