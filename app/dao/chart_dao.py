# app/dao/chart_dao.py
from typing import List, Optional, Dict, Any
from sqlalchemy import desc, or_
from datetime import datetime

from .base_dao import BaseDAO
from app.model.db.movie_model import Chart
from app.utils.log_util import debug, info, warning, error, critical


class ChartDAO(BaseDAO[Chart]):
    """
    Chart数据访问对象，处理与Chart模型相关的数据库操作

    继承自BaseDAO，实现了单例模式
    """

    def __init__(self):
        """
        初始化ChartDAO，设置模型为Chart

        日志记录：
        - 记录ChartDAO的初始化，便于追踪DAO对象的创建
        """
        super().__init__(Chart)
        info("ChartDAO initialized")

    def get_by_name_or_create(self, chart: Chart):
        """
        根据名称获取榜单，如果不存在则创建新的榜单

        Args:
            chart (Chart): 要获取或创建的榜单对象

        Returns:
            Chart: 获取到的或新创建的榜单对象
            None: 如果发生错误

        日志记录：
        - 记录尝试获取或创建榜单的操作
        - 记录是否找到现有榜单或创建了新榜单
        - 记录可能发生的错误
        """
        try:
            debug(f"Attempting to get or create chart: {chart.name}")
            flg = self.get_by_name(chart.name)
            if flg is None:
                info(f"Creating new chart: {chart.name}")
                return self.create(chart)
            else:
                info(f"Chart already exists: {chart.name}")
                return flg
        except Exception as e:
            error(f"An error occurred while getting or creating chart: {e}")
            return None

    def get_by_name(self, name: str) -> Optional[Chart]:
        """
        根据名称获取榜单

        Args:
            name (str): 榜单名称

        Returns:
            Optional[Chart]: 如果找到则返回Chart对象，否则返回None

        日志记录：
        - 记录尝试获取榜单的操作
        - 记录是否成功找到榜单
        - 记录可能发生的错误
        """
        try:
            debug(f"Attempting to get chart by name: {name}")
            obj = self.db.session.query(Chart).filter(Chart.name == name).first()
            if obj:
                info(f"Chart found: {name}")
            else:
                info(f"Chart not found: {name}")
            return obj
        except Exception as e:
            error(f"Error in get_by_name: {e}")
            self.db.session.rollback()
            return None

    def find_by_keyword(self, keyword: str) -> List[Chart]:
        """
        根据关键词搜索榜单

        Args:
            keyword (str): 搜索关键词

        Returns:
            List[Chart]: 符合搜索条件的榜单列表

        日志记录：
        - 记录搜索操作的开始
        - 记录搜索结果的数量
        """
        debug(f"Searching charts with keyword: {keyword}")
        search = f"%{keyword}%"
        results = self.db.session.query(Chart).filter(
            or_(
                Chart.name.like(search),
                Chart.description.like(search)
            )
        ).all()
        info(f"Found {len(results)} charts matching keyword: {keyword}")
        return results

    def get_recent_charts(self, limit: int = 10) -> List[Chart]:
        """
        获取最近创建的榜单

        Args:
            limit (int): 返回的榜单数量限制，默认为10

        Returns:
            List[Chart]: 最近创建的榜单列表

        日志记录：
        - 记录获取最近榜单的操作
        - 记录实际获取到的榜单数量
        """
        debug(f"Getting {limit} recent charts")
        results = self.db.session.query(Chart).order_by(desc(Chart.created_at)).limit(limit).all()
        info(f"Retrieved {len(results)} recent charts")
        return results

    def update_chart_data(self, chart_id: int, new_data: Dict[str, Any]) -> Optional[Chart]:
        """
        更新榜单数据 TODO 没有data字段，需要重新处理

        Args:
            chart_id (int): 榜单ID
            new_data (Dict[str, Any]): 新的榜单数据

        Returns:
            Optional[Chart]: 更新后的榜单对象，如果榜单不存在则返回None

        日志记录：
        - 记录尝试更新榜单数据的操作
        - 记录更新操作是否成功
        - 记录榜单不存在的情况
        """
        debug(f"Attempting to update chart data for chart_id: {chart_id}")
        chart = self.db.session.query(Chart).filter(Chart.id == chart_id).first()
        if chart:
            for key, value in new_data.items():
                if hasattr(chart, key):
                    setattr(chart, key, value)
            chart.updated_at = datetime.utcnow()
            self.db.session.commit()
            info(f"Successfully updated chart data for chart_id: {chart_id}")
            return chart
        else:
            warning(f"Chart not found for chart_id: {chart_id}")
        return None

    def get_charts_by_type(self, chart_type_id: int) -> List[Chart]:
        """
        根据榜单类型获取榜单列表

        Args:
            chart_type_id (int): 榜单类型ID

        Returns:
            List[Chart]: 指定类型的榜单列表

        日志记录：
        - 记录获取特定类型榜单的操作
        - 记录获取到的榜单数量
        """
        debug(f"Getting charts for chart_type_id: {chart_type_id}")
        results = self.db.session.query(Chart).filter(Chart.chart_type_id == chart_type_id).all()
        info(f"Found {len(results)} charts for chart_type_id: {chart_type_id}")
        return results