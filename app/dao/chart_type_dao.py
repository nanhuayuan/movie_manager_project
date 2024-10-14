# app/dao/chart_type_dao.py
from typing import List, Optional
from .base_dao import BaseDAO
from app.model.db.movie_model import ChartType
from flask import current_app


class ChartTypeDAO(BaseDAO[ChartType]):
    def __init__(self):
        super().__init__(ChartType)

    def get_by_name(self, name: str) -> Optional[ChartType]:
        """
        根据名称获取榜单类型

        Args:
            name: 榜单类型名称

        Returns:
            Optional[ChartType]: 如果找到则返回 ChartType 对象，否则返回 None
        """
        try:
            return self.db.session.query(ChartType).filter(ChartType.name == name).first()
        except Exception as e:
            current_app.logger.error(f"Error in get_by_name: {e}")
            self.db.session.rollback()
            return None

    def get_all_active(self) -> List[ChartType]:
        """
        获取所有激活状态的榜单类型

        Returns:
            List[ChartType]: 激活状态的榜单类型列表
        """
        return self.db.session.query(ChartType).filter(ChartType.is_active == True).all()

    def update(self, chart_type_id: int, name: Optional[str] = None,
               description: Optional[str] = None, is_active: Optional[bool] = None) -> Optional[ChartType]:
        """
        更新榜单类型

        Args:
            chart_type_id: 榜单类型ID
            name: 新的名称（可选）
            description: 新的描述（可选）
            is_active: 新的激活状态（可选）

        Returns:
            Optional[ChartType]: 更新后的榜单类型对象，如果未找到则返回 None
        """
        try:
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
            return chart_type
        except Exception as e:
            current_app.logger.error(f"Error in update: {e}")
            self.db.session.rollback()
            return None
