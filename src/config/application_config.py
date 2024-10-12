import yaml
import os


def load_config(config_path="configbak/settings.yaml"):
    """加载配置文件"""
    with open(config_path, "r", encoding="utf-8") as file:
        config = yaml.safe_load(file)
    return config


# 在程序的开始部分调用
config = load_config()

# 例如，获取数据库配置
db_config = config['database']
print(db_config)
