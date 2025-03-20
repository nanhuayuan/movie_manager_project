from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any

from app.config.app_config import AppConfig
from app.dao import ActorDAO
from app.model.db.movie_model import Actor, Movie
from app.services.base_service import BaseService
from app.config.log_config import debug, info, warning, error, critical


@dataclass
class ActorService(BaseService[Actor, ActorDAO]):
    def __init__(self):
        super().__init__()
        info("ActorService initialized")

    def __init__new(self, config, http_util, parser, actor_service):
        self.config = config
        self.scraper_from = config.get('from', 'javdb')
        self.scraper_web_config = config.get(self.scraper_from, {})
        self.base_url = self.scraper_web_config.get('domain', "https://javdb.com")
        self.cookie = self.scraper_web_config.get('cookie', '')
        self.http_util = http_util
        self.parser = parser
        self.actor_service = actor_service

        # 初始化 不在这里用 ActorService
        self.actor_processor = ActorService(
            config=AppConfig().get_web_scraper_config(),
            http_util=self.http_util,
            parser=self.parser,
            actor_service=self.service_map['actor']
        )

    def search_actor(self, actor_name: str) -> Dict[str, Any]:
        """搜索演员信息"""
        # 搜索演员的代码...

    def get_actor_details(self, actor_uri: str) -> Dict[str, Any]:
        """获取演员详细信息"""
        # 获取演员详情的代码...

    def get_or_create_actor(self, actor_info: Dict[str, Any]) -> Optional[Actor]:
        """获取或创建演员记录"""
        # 获取或创建演员的代码...

    def set_actor_details(self, actor: Actor, actor_info: Dict[str, Any],scraper_from = 'javdb') -> None:
        """设置演员详细信息"""
        # 设置基本信息
        if 'photo' in actor_info:
            actor.pic = actor_info['photo']

        # 设置名称相关信息
        if 'name_cn' in actor_info:
            actor.name_cn = actor_info['name_cn']
        if 'name_en' in actor_info:
            actor.name_en = actor_info['name_en']

        # 设置IDs
        if 'javdb_id' in actor_info:
            actor.javdb_id = actor_info['javdb_id']

        # 设置URI
        if 'uri' in actor_info:
            if scraper_from == 'javdb':
                actor.javdb_uri = actor_info['uri']

        # 设置身体数据
        if 'birthday' in actor_info and actor_info['birthday']:
            try:
                actor.birthday = actor_info['birthday']
            except Exception as e:
                error(f"设置演员生日失败: {str(e)}")

        if 'age' in actor_info:
            actor.age = actor_info.get('age', 0)
        if 'cupsize' in actor_info:
            actor.cupsize = actor_info.get('cupsize', '')
        if 'height' in actor_info:
            actor.height = actor_info.get('height', 0)
        if 'bust' in actor_info:
            actor.bust = actor_info.get('bust', 0)
        if 'waist' in actor_info:
            actor.waist = actor_info.get('waist', 0)
        if 'hip' in actor_info:
            actor.hip = actor_info.get('hip', 0)

        # 设置其他信息
        if 'hometown' in actor_info:
            actor.hometown = actor_info.get('hometown', '')
        if 'hobby' in actor_info:
            actor.hobby = actor_info.get('hobby', '')

    def update_actor_info(self, actor: Actor, actor_info: Dict[str, Any]) -> None:
        """更新演员信息"""
        # 已有的演员记录，更新非空字段
        update_needed = False

        if 'photo' in actor_info and actor_info['photo'] and not actor.pic:
            actor.pic = actor_info['photo']
            update_needed = True

        # 更新名称相关信息
        if 'name_cn' in actor_info and actor_info['name_cn'] and not actor.name_cn:
            actor.name_cn = actor_info['name_cn']
            update_needed = True
        if 'name_en' in actor_info and actor_info['name_en'] and not actor.name_en:
            actor.name_en = actor_info['name_en']
            update_needed = True

        # 更新IDs
        if 'javdb_id' in actor_info and actor_info['javdb_id'] and not actor.javdb_id:
            actor.javdb_id = actor_info['javdb_id']
            update_needed = True

        # 更新URI
        if scraper_from == 'javdb':
            if 'uri' in actor_info and actor_info['uri'] and not actor.javdb_uri:
                actor.javdb_uri = actor_info['uri']
                update_needed = True

        # 更新身体数据
        default_date = datetime.date(1970, 1, 1)
        if 'birthday' in actor_info and actor_info['birthday'] and actor.birthday == default_date:
            try:
                actor.birthday = actor_info['birthday']
                update_needed = True
            except Exception as e:
                error(f"更新演员生日失败: {str(e)}")

        if 'age' in actor_info and actor_info['age'] and actor.age == 0:
            actor.age = actor_info['age']
            update_needed = True
        if 'cupsize' in actor_info and actor_info['cupsize'] and not actor.cupsize:
            actor.cupsize = actor_info['cupsize']
            update_needed = True
        if 'height' in actor_info and actor_info['height'] and actor.height == 0:
            actor.height = actor_info['height']
            update_needed = True
        if 'bust' in actor_info and actor_info['bust'] and actor.bust == 0:
            actor.bust = actor_info['bust']
            update_needed = True
        if 'waist' in actor_info and actor_info['waist'] and actor.waist == 0:
            actor.waist = actor_info['waist']
            update_needed = True
        if 'hip' in actor_info and actor_info['hip'] and actor.hip == 0:
            actor.hip = actor_info['hip']
            update_needed = True

        # 更新其他信息
        if 'hometown' in actor_info and actor_info['hometown'] and not actor.hometown:
            actor.hometown = actor_info['hometown']
            update_needed = True
        if 'hobby' in actor_info and actor_info['hobby'] and not actor.hobby:
            actor.hobby = actor_info['hobby']
            update_needed = True

        # 如果有更新，则保存到数据库
        if update_needed:
            try:
                self.service_map['actor'].update(actor)
                info(f"更新演员信息成功: {actor.name}")
            except Exception as e:
                error(f"更新演员信息失败: {str(e)}")
