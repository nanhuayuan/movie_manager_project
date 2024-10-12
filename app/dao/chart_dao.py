# app/dao/chart_dao.py
from typing import List, Optional, Dict, Any
from sqlalchemy import desc, or_
from datetime import datetime

from .base_dao import BaseDAO
from app.model.db.movie_model import Chart
from app.utils.db_util import db


class ChartDAO(BaseDAO[Chart]):
    """
    Chart数据访问对象，处理与Chart模型相关的数据库操作

    继承自BaseDAO，实现了单例模式
    """

    def __init__(self):
        """初始化ChartDAO，设置模型为Chart"""
        super().__init__(Chart)

    def get_by_name_or_create(self, chart: Chart):
        try:
            flg = self.get_by_name(chart.name)
            if flg is None:
                return self.chart_dao.create(chart)
            else:
                return flg
        except Exception as e:
            # 处理异常
            print(f"An error occurred: {e}")
            return None

    def get_by_name(self, name: str) -> Optional[Chart]:

        with db.session_scope() as session:
            obj =  session.query(Chart).filter(Chart.name == name).first()
            return self._clone_object(obj, session) if obj else None

    def find_by_keyword(self, keyword: str) -> List[Chart]:
        """
        根据关键词搜索榜单

        Args:
            keyword (str): 搜索关键词

        Returns:
            List[Chart]: 符合搜索条件的榜单列表
        """
        with db.session_scope() as session:
            search = f"%{keyword}%"
            return session.query(Chart).filter(
                or_(
                    Chart.name.like(search),
                    Chart.description.like(search)
                )
            ).all()

    def get_recent_charts(self, limit: int = 10) -> List[Chart]:
        """
        获取最近创建的榜单

        Args:
            limit (int): 返回的榜单数量限制，默认为10

        Returns:
            List[Chart]: 最近创建的榜单列表
        """
        with db.session_scope() as session:
            return session.query(Chart).order_by(desc(Chart.created_at)).limit(limit).all()

    def update_chart_data(self, chart_id: int, new_data: Dict[str, Any]) -> Optional[Chart]:
        """
        更新榜单数据 TODO 没有data字段，需要重新处理

        Args:
            chart_id (int): 榜单ID
            new_data (Dict[str, Any]): 新的榜单数据

        Returns:
            Optional[Chart]: 更新后的榜单对象，如果榜单不存在则返回None
        """
        with db.session_scope() as session:
            chart = session.query(Chart).filter(Chart.id == chart_id).first()
            if chart:
                for key, value in new_data.items():
                    if hasattr(chart, key):
                        setattr(chart, key, value)
                chart.updated_at = datetime.utcnow()
                session.flush()
                session.refresh(chart)
                return chart
            return None

    def get_charts_by_type(self, chart_type_id: int) -> List[Chart]:
        """
        根据榜单类型获取榜单列表

        Args:
            chart_type_id (str): 榜单类型

        Returns:
            List[Chart]: 指定类型的榜单列表
        """
        with db.session_scope() as session:
            return session.query(Chart).filter(Chart.chart_type_id == chart_type_id).all()