from app.config.config_app import AppConfig


class QBittorrentUtil:
    _instance = None

    def __new__(cls):
        """
        该函数实现单例模式，确保类仅有一个实例。首次调用时：
        1.通过super().__new__(cls)创建实例；
        2.初始化，加载配置；
        3.从配置中获取信息；
        4.使用这些信息创建对象并存储在类属性_instance.client中。 之后的调用直接返回已有实例。
        """
        if cls._instance is None:
            cls._instance = super().__new__(cls)

            """初始化，加载配置"""
            config_loader = AppConfig()
            # 从配置文件中获取数据库连接URL
            uri = self._construct_url(qb_config)
            self.echo = qb_config.get('echo', False)
            self.pool_size = qb_config.get('pool_size', 5)
            self.echo_pool = qb_config.get('echo_pool', False)
            self.max_overflow = qb_config.get('max_overflow', 10)

            # 从配置文件中获取数据库连接URL
            api_url = config.get('api_url', 'http://localhost:6363')
            api_key = config.get('api_key', '')

            # 暂时用不到配置
            cls._instance.client = JellyfinapiClient(
                x_emby_token=api_key,
                server_url=api_url)

        return cls._instance
    def _construct_url(self, qb_config):
        """构建URL"""

        host = qb_config.get('host', '127.0.0.1')
        port = qb_config.get('port', 6363)
        user = qb_config.get('username', '')
        password = qb_config.get('password', '')
        dbname = qb_config.get('dbname', '')

        # 构建 MySQL 的数据库连接 URL
        return f"mysql+pymysql://{user}:{password}@{host}:{port}/{dbname}"

    def __init__(self):
        """
        初始化Jellyfin客户端工具

        这个方法使用提供的凭证设置Jellyfin客户端，并连接到指定的Jellyfin服务器。

        参数:
            server_url (str): Jellyfin服务器的URL
            api_key (str): 用于认证的API密钥
            device_id (str): 此客户端实例的唯一标识符
            client_name (str): 此客户端应用程序的名称
        """
        """初始化，加载配置"""
        config_loader = AppConfig()
        config = config_loader.get_jellyfin_config()

        server_url = config.get('api_url', 'http://localhost:8096')

        self.user_id = config.get('user_id', '')
        self.item_id = config.get('item_id', '')
        self.playlists_id = config.get('playlists_id', '')

        self.items_controller = self.client.items
        self.item_update_controller = self.client.item_update
        self.user_library_controller = self.client.user_library
        self.library_controller = self.client.library
        self.playlists_controller = self.client.playlists

        # self.client.config.app(deviceName=client_name, deviceId=device_id, version="1.0.0")
        # self.client.config.data["auth.ssl"] = True
        # self.client.config.data["auth.server"] = server_url
        # self.client.config.data["auth.apikey"] = api_key
        # self.client.auth.connect_to_address(server_url)
        # self.client.auth.apikey = api_key
        self.logger = logging.getLogger(__name__)
        logging.info(f"Jellyfin客户端已初始化，服务器地址: {server_url}")
    def download_by_qbittorrent_one(movie_info, retry_count=1, max_retry_count=10):
        if len(movie_info.magnet_list) <= 0:
            logger.info("||||||||||||||||||||||||||||||||没有磁力||||||||||||||||||||||||||||||||】，编号：【" + movie_info.code + "】")

        magnet = movie_info.magnet_list[0]
        logger.info(
            "↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓开始下载↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓】，编号：【" + movie_info.code + "】，：磁力【" + magnet)

        while (retry_count <= max_retry_count):
            try:
                # 请求并解析
                qb = Client(download_qbittorrent_url, verify=False)
                qb.download_from_link(magnet)
                logger.info(
                    "↓√↓√↓√↓√↓√↓√↓√↓√↓√↓√↓√↓√↓√↓√↓√↓√↓√磁力下载完成↓√↓√↓√↓√↓√↓√↓√↓√↓√↓√↓√↓√↓√↓√↓√↓√↓√-->编号：【" + movie_info.code + "】，：磁力【" + magnet)
                return True
            except (LoginRequired, HTTPError) as e:
                logger.error("发生了以下异常：", e.__class__.__name__)
                logger.error("↓×↓×↓×↓×↓×↓×↓×↓×↓×↓×↓×↓×↓×↓×↓第【：" + str(retry_count) + "】几次错误，正在重试")
                logger.error(f"Operation failed: {e}")
                retry_count += 1
                time.sleep(random.randint(10, 30))  # 函数的参数是等待的时间，单位是秒

        return False