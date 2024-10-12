# 首先安装依赖
# pip install dependency-injector

from dependency_injector import containers, providers
from dependency_injector.wiring import inject, Provide


# 1. 创建一些基础服务类
class Database:
    def __init__(self, connection_string: str):
        self.connection_string = connection_string

    def connect(self):
        print(f"连接到数据库: {self.connection_string}")


class UserRepository:
    def __init__(self, database: Database):
        self.database = database

    def get_user(self, user_id: int):
        self.database.connect()
        return f"获取用户 {user_id} 的信息"


class UserService:
    def __init__(self, user_repository: UserRepository):
        self.user_repository = user_repository

    def get_user_info(self, user_id: int):
        return self.user_repository.get_user(user_id)


# 2. 创建容器类来管理依赖
class Container(containers.DeclarativeContainer):
    # 配置
    config = providers.Configuration()

    # 数据库依赖
    database = providers.Singleton(
        Database,
        connection_string=config.db.connection_string,
    )

    # 用户仓储依赖
    user_repository = providers.Factory(
        UserRepository,
        database=database,
    )

    # 用户服务依赖
    user_service = providers.Factory(
        UserService,
        user_repository=user_repository,
    )


# 3. 创建应用类
class Application:
    @inject
    def __init__(self, user_service: UserService = Provide[Container.user_service]):
        self.user_service = user_service

    def run(self):
        user_info = self.user_service.get_user_info(1)
        print(user_info)


# 4. 运行示例
if __name__ == "__main__":
    # 创建并配置容器
    container = Container()
    container.config.db.connection_string.from_value("postgresql://user:pass@localhost:5432/db")

    # 将容器与应用程序绑定
    container.wire(modules=[__name__])

    # 创建并运行应用
    app = Application()
    app.run()