import requests

class JellyfinChecker:
    def __init__(self, jellyfin_config):
        self.base_url = jellyfin_config['base_url']
        self.api_key = jellyfin_config['api_key']

    def movie_exists_in_jellyfin(self, title):
        url = f"{self.base_url}/Items"
        headers = {
            "X-Emby-Token": self.api_key
        }
        params = {
            "searchTerm": title,
            "IncludeItemTypes": "Movie",
        }
        response = requests.get(url, headers=headers, params=params)
        return response.json()['TotalRecordCount'] > 0
