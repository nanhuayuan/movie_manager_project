import requests

class MovieChecker:
    def __init__(self, jellyfin_client, everything_client):
        self.jellyfin = jellyfin_client
        self.everything = everything_client

    def check_in_jellyfin(self, movie_id: str):
        # 使用 Jellyfin API 检查电影是否存在
        response = self.jellyfin.get(f'/Items?searchTerm={movie_id}')
        if response.status_code == 200:
            items = response.json().get('Items', [])
            if items:
                return True
        return False

    def check_locally(self, movie_serial: str):
        # 使用 Everything API 检查本地文件
        query = {"search": movie_serial}
        response = requests.get(f'http://localhost:8888/', params=query)
        if response.status_code == 200:
            results = response.json().get('results', [])
            if results:
                return True
        return False

    def check_movie(self, movie_serial: str):
        if self.check_in_jellyfin(movie_serial):
            print(f"电影 {movie_serial} 存在于 Jellyfin 中")
        elif self.check_locally(movie_serial):
            print(f"电影 {movie_serial} 存在于本地文件系统中")
        else:
            print(f"电影 {movie_serial} 不存在")
