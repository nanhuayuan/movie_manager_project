import requests

class QbittorrentManager:
    def __init__(self, qbittorrent_config):
        self.base_url = qbittorrent_config['base_url']
        self.session = requests.Session()
        self.session.post(f"{self.base_url}/login", data={
            'username': qbittorrent_config['username'],
            'password': qbittorrent_config['password']
        })

    def add_torrent(self, magnet_link):
        response = self.session.post(f"{self.base_url}/command/download", data={'urls': magnet_link})
        return response.status_code == 200
