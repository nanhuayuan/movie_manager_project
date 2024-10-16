# app/dao/chart_type_dao.py
from typing import List, Optional
from .base_dao import BaseDAO
from app.model.db.movie_model import ChartType
from flask import current_app
from app.utils.log_util import debug, info, warning, error, critical

class ChartTypeDAO(BaseDAO[ChartType]):
    """
    ChartType数据访问对象，处理与ChartType模型相关的数据库操作

    继承自BaseDAO，实现了单例模式
    """

    def __init__(self):
        """
        初始化ChartTypeDAO，设置模型为ChartType

        日志记录：
        - 记录ChartTypeDAO的初始化
        """
        super().__init__(ChartType)
        info("ChartTypeDAO initialized")

    def get_by_name(self, name: str) -> Optional[ChartType]:
        """
        根据名称获取榜单类型

        Args:
            name (str): 榜单类型名称

        Returns:
            Optional[ChartType]: 如果找到则返回 ChartType 对象，否则返回 None

        日志记录：
        - 记录尝试获取榜单类型的操作
        - 记录是否成功找到榜单类型
        - 记录可能发生的错误
        """
        try:
            debug(f"Attempting to get chart type by name: {name}")
            chart_type = self.db.session.query(ChartType).filter(ChartType.name == name).first()
            if chart_type:
                info(f"Chart type found: {name}")
            else:
                info(f"Chart type not found: {name}")
            return chart_type
        except Exception as e:
            error(f"Error in get_by_name: {e}")
            self.db.session.rollback()
            return None

    def get_all_active(self) -> List[ChartType]:
        """
        获取所有激活状态的榜单类型

        Returns:
            List[ChartType]: 激活状态的榜单类型列表

        日志记录：
        - 记录获取激活榜单类型的操作
        - 记录获取到的榜单类型数量
        """
        debug("Getting all active chart types")
        active_types = self.db.session.query(ChartType).filter(ChartType.is_active == True).all()
        info(f"Retrieved {len(active_types)} active chart types")
        return active_types

    def update(self, chart_type_id: int, name: Optional[str] = None,
               description: Optional[str] = None, is_active: Optional[bool] = None) -> Optional[ChartType]:
        """
        更新榜单类型

        Args:
            chart_type_id (int): 榜单类型ID
            name (Optional[str]): 新的名称（可选）
            description (Optional[str]): 新的描述（可选）
            is_active (Optional[bool]): 新的激活状态（可选）

        Returns:
            Optional[ChartType]: 更新后的榜单类型对象，如果未找到则返回 None

        日志记录：
        - 记录尝试更新榜单类型的操作
        - 记录更新操作是否成功
        - 记录可能发生的错误
        """
        try:
            debug(f"Attempting to update chart type with id: {chart_type_id}")
            chart_type = self.db.session.query(ChartType).filter(ChartType.id == chart_type_id).first()
            if chart_type:
                if name is not None:
                    chart_type.name = name
                if description is not None:
                    chart_type.description = description
                if is_active is not None:
                    chart_type.is_active = is_active
                self.db.session.commit()
                self.db.session.refresh(chart_type)
                info(f"Successfully updated chart type with id: {chart_type_id}")
                return chart_type
            else:
                warning(f"Chart type not found with id: {chart_type_id}")
            return None
        except Exception as e:
            error(f"Error in update: {e}")
            self.db.session.rollback()
            return None