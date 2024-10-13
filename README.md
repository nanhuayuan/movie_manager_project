# 目录结构
## requirements.txt

###导出requirements.txt
参考以下链接：[python导出requirements.txt的几种方法](https://blog.csdn.net/zly_Always_be/article/details/142731248)
使用Conda导出requirements.txt：
```
conda list -e > requirements.txt
```

```
pip list --format=freeze >requirement.txt
```

pipreqs输出当前项目的依赖
```
pip install pipreqs
pipreqs . --encoding=utf8 --force

```
### 导入
参考：[pip修改镜像源，使用requirements.txt文件](https://blog.csdn.net/weixin_53134351/article/details/140673247)
```
pip install -r requirements.txt

pip3 install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/

pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

```

常用镜像源
```
    清华大学 ：https://pypi.tuna.tsinghua.edu.cn/simple/
     
    阿里云：http://mirrors.aliyun.com/pypi/simple/
     
    中国科学技术大学 ：http://pypi.mirrors.ustc.edu.cn/simple/
     
    华中科技大学：http://pypi.hustunique.com/
     
    豆瓣源：http://pypi.douban.com/simple/
     
    腾讯源：http://mirrors.cloud.tencent.com/pypi/simple/
     
    华为镜像源：https://repo.huaweicloud.com/repository/pypi/simple/
```   

临时修改镜像源
```
    pip install [包名] -i [URL]
     
    # 示例
    pip install xx -i https://pypi.tuna.tsinghua.edu.cn/simple
    # 或
    pip install -i https://pypi.tuna.tsinghua.edu.cn/simple pytest
    # 或
    pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple  --trusted-host pypi.tuna.tsinghua.edu.cn
```
永久修改镜像源 
```
    pip config set global.index-url http://mirrors.aliyun.com/pypi/simple/
     
    pip config set install.trusted-host mirrors.aliyun.com
```
查看已有镜像源
```
pip config list
```
### 项目目录
```
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
```