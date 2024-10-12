# 目录结构

myproject/                      # 项目根目录
├── README.md
├── requirements.txt
├── setup.py
├── myproject/                  # 主代码目录
│   ├── __init__.py
│   ├── main.py                 # 应用入口点
│   ├── config/                 # 配置模块目录
│   │   ├── __init__.py
│   │   ├── base_config.py      # 基础配置类
│   │   ├── app_config.py       # 应用配置类
│   │   └── log_config.py       # 日志配置类
│   ├── core/                   # 核心业务逻辑
│   │   ├── __init__.py
│   │   └── ...
│   └── utils/
│       ├── __init__.py
│       └── ...
├── tests/                      # 测试目录
│   ├── __init__.py
│   ├── test_app_config.py
│   └── test_log_config.py
└── config/                     # 配置文件目录
    ├── app.default.yml         # 应用默认配置
    ├── app.development.yml     # 应用开发环境配置
    ├── app.production.yml      # 应用生产环境配置
    ├── app.testing.yml         # 应用测试环境配置
    ├── logging.default.yml     # 日志默认配置
    ├── logging.development.yml # 日志开发环境配置
    └── logging.production.yml  # 日志生产环境配置