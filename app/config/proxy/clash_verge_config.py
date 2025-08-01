import os
from pathlib import Path
from typing import Dict, Optional, List

from .base_proxy_config import BaseProxyConfig

# 尝试导入 psutil，如果失败则使用备用方案
try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False


class ClashVergeConfig(BaseProxyConfig):
    """Clash.Verge 代理配置实现类"""
    
    @property
    def proxy_type(self) -> str:
        return "clash_verge"
    
    @property
    def default_config_paths(self) -> List[Path]:
        """Clash.Verge 默认配置路径"""
        paths = []
        
        # Windows 默认路径
        if os.name == 'nt' and 'USERPROFILE' in os.environ:
            # 新版 Clash Verge Rev 路径
            verge_rev_path = self._expand_user_path(
                "C:/Users/{user}/AppData/Roaming/io.github.clash-verge-rev.clash-verge-rev/config.yaml"
            )
            paths.append(verge_rev_path)
            
            # 旧版 Clash Verge 路径
            verge_path = self._expand_user_path(
                "C:/Users/{user}/AppData/Roaming/clash-verge/config.yaml"  
            )
            paths.append(verge_path)
        
        # macOS 路径
        if os.name == 'posix':
            macos_paths = [
                self._get_user_home() / "Library/Application Support/io.github.clash-verge-rev.clash-verge-rev/config.yaml",
                self._get_user_home() / "Library/Application Support/clash-verge/config.yaml"
            ]
            paths.extend(macos_paths)
        
        # Linux 路径
        linux_paths = [
            self._get_user_home() / ".config/clash-verge/config.yaml",
            self._get_user_home() / ".config/io.github.clash-verge-rev.clash-verge-rev/config.yaml"
        ]
        paths.extend(linux_paths)
        
        # 通用备用路径
        backup_paths = [
            Path.cwd() / "clash-verge-config.yaml",
            Path.cwd() / "config.yaml"
        ]
        paths.extend(backup_paths)
        
        return paths
    
    def is_available(self) -> bool:
        """检查 Clash.Verge 是否可用"""
        # 检查进程是否运行
        if self._is_process_running():
            return True
            
        # 检查配置文件是否存在
        return self.get_config_file_path() is not None
    
    def _is_process_running(self) -> bool:
        """检查 Clash.Verge 进程是否运行中"""
        if not HAS_PSUTIL:
            # 如果没有 psutil，尝试使用系统命令
            return self._check_process_without_psutil()
        
        process_names = [
            'clash-verge.exe', 
            'Clash Verge.exe',
            'clash-verge-service.exe',
            'clash-verge',
            'Clash Verge'
        ]
        
        try:
            for proc in psutil.process_iter(['name']):
                try:
                    if proc.info['name'] in process_names:
                        return True
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
        except Exception:
            # 如果 psutil 出错，回退到系统命令
            return self._check_process_without_psutil()
        
        return False
    
    def _check_process_without_psutil(self) -> bool:
        """不使用 psutil 检查进程（备用方案）"""
        try:
            if os.name == 'nt':  # Windows
                import subprocess
                result = subprocess.run(['tasklist', '/fi', 'imagename eq *verge*'], 
                                      capture_output=True, text=True, timeout=5)
                return 'verge' in result.stdout.lower()
            else:  # Linux/macOS
                import subprocess
                result = subprocess.run(['pgrep', '-f', 'clash.*verge'], 
                                      capture_output=True, text=True, timeout=5)
                return bool(result.stdout.strip())
        except Exception:
            # 如果系统命令也失败，返回 False
            return False
    
    def get_config_file_path(self) -> Optional[Path]:
        """获取 Clash.Verge 配置文件路径"""
        for path in self.default_config_paths:
            if path.exists() and path.is_file():
                # 验证这是一个有效的 Clash 配置文件
                if self._is_valid_clash_config(path):
                    return path
        return None
    
    def _is_valid_clash_config(self, config_path: Path) -> bool:
        """验证配置文件是否为有效的 Clash 配置"""
        try:
            config_data = self._load_yaml_config(config_path)
            # 检查是否包含 Clash 必要的配置项
            required_fields = ['port', 'socks-port', 'external-controller']
            return any(field in config_data for field in required_fields)
        except:
            return False
    
    def parse_config_file(self, config_path: Path) -> Dict:
        """解析 Clash.Verge 配置文件"""
        config_data = self._load_yaml_config(config_path)
        
        # 获取API控制地址和密钥
        controller = config_data.get('external-controller', '')
        secret = config_data.get('secret', '')
        
        # 获取代理端口（Clash.Verge 可能使用不同字段）
        proxy_port = (
            config_data.get('mixed-port') or 
            config_data.get('port') or 
            config_data.get('http-port') or 
            7890
        )
        
        if not controller:
            raise ValueError("配置文件中缺少external-controller配置")
        
        # 解析API主机和端口
        host = '127.0.0.1'  # 默认主机
        api_port = None
        
        if ':' in controller:
            host_part, port_part = controller.split(':', 1)
            if host_part:  # 如果主机部分不为空
                host = host_part
            api_port = int(port_part)
        else:
            # 如果只有端口号
            api_port = int(controller)
        
        if api_port is None:
            raise ValueError("无法解析API端口")
        
        return {
            'host': host,
            'api_port': api_port,
            'proxy_port': proxy_port,
            'secret': secret.strip() if secret else None,
            'config_path': str(config_path)
        }