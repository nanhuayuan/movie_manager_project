import yaml

class ConfigLoader:
    def __init__(self, config_file='../configbak/application.yml'):
        with open(config_file, 'r') as file:
            self.config = yaml.safe_load(file)

    def get_database_config(self):
        return self.config['database']

    def get_jellyfin_config(self):
        return self.config['jellyfin']

    def get_qbittorrent_config(self):
        return self.config['qbittorrent']



# 以下为调用
from app.config.app_config import ConfigLoader

def main():
    config_loader = ConfigLoader()
    db_config = config_loader.get_database_config()
    jellyfin_config = config_loader.get_jellyfin_config()
    qbittorrent_config = config_loader.get_qbittorrent_config()

    print(db_config)
    print(jellyfin_config)
    print(qbittorrent_config)

if __name__ == "__main__":
    main()