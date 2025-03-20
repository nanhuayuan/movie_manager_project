import os
import yaml
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime


class ClashConfig:
    """Clash配置管理类，负责查找和解析Clash配置文件"""

    def __init__(self):
        """初始化Clash配置管理器"""
        self.config = None
        self.last_refresh_time = None
        # 刷新间隔（5分钟）
        self.refresh_interval = 300

    def get_clash_config_path(self) -> Path:
        """自动查找Clash配置文件路径（支持Windows和跨平台）"""
        # Windows默认路径（Clash for Windows）
        if 'USERPROFILE' in os.environ:
            win_path = Path(os.environ['USERPROFILE']) / 'AppData/Roaming/Clash for Windows/Profiles'
            if win_path.exists():
                for file in win_path.iterdir():
                    if file.suffix in ('.yaml', '.yml') and file.name.startswith('config'):
                        return file

        # 通用路径尝试
        paths = [
            Path.home() / ".config/clash/config.yaml",  # Linux/macOS
            Path(os.getcwd()) / "config.yaml"  # 当前目录
        ]

        for p in paths:
            if p.exists():
                return p

        raise FileNotFoundError("Clash配置文件未找到")

    def parse_clash_config(self, config_path=None) -> Dict:
        """解析Clash配置文件获取API信息"""
        if not config_path:
            config_path = self.get_clash_config_path()

        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
        except Exception as e:
            raise ValueError(f"配置文件解析失败: {str(e)}")

        # 获取API控制地址和密钥
        controller = config.get('external-controller', '')
        secret = config.get('secret', '')

        # 获取代理端口
        proxy_port = config.get('mixed-port', config.get('port', 7890))

        if not controller:
            raise ValueError("配置文件中缺少external-controller配置")

        # 解析API主机和端口
        host = '127.0.0.1'  # 默认主机
        api_port = None

        if ':' in controller:
            host_part, port_part = controller.split(':', 1)
            # 如果主机部分不为空，则使用配置文件中的主机
            if host_part:
                host = host_part
            # 解析API端口
            api_port = int(port_part)

        return {
            'host': host,
            'api_port': api_port,  # API控制端口
            'proxy_port': proxy_port,  # 代理端口
            'secret': secret.strip() if secret else None,
            'config_path': str(config_path)
        }

    def refresh_config(self) -> Dict:
        """刷新Clash配置信息"""
        self.config = self.parse_clash_config()
        self.last_refresh_time = datetime.now()
        return self.config

    def get_config(self, force_refresh=False) -> Dict:
        """获取Clash配置，如果超过刷新间隔则自动刷新"""
        now = datetime.now()

        if (force_refresh or
                not self.config or
                not self.last_refresh_time or
                (now - self.last_refresh_time).total_seconds() > self.refresh_interval):
            return self.refresh_config()

        return self.config


if __name__ == '__main__':
    # 测试代码
    clash_config = ClashConfig()
    config = clash_config.get_config()
    print(f"API地址: {config['host']}:{config['api_port']}")
    print(f"代理端口: {config['proxy_port']}")
    print(f"密钥: {config['secret'] or '无'}")
    print(f"配置文件路径: {config['config_path']}")