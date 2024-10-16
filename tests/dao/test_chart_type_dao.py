# tests/dao/test_chart_type_dao.py
import pytest
from app.dao.chart_type_dao import ChartTypeDAO
from app.model.db.movie_model import ChartType
from app.utils.db_util import db


class TestChartTypeDAO:
    @pytest.fixture
    def dao(self):
        return ChartTypeDAO()

    @pytest.fixture
    def setup_database(self):
        # 在每个测试前设置数据库
        with db.session_scope() as session:
            session.query(ChartType).delete()
            session.commit()

    def test_create(self, dao, setup_database):
        chart_type = dao.create(name="折线图", description="用于展示趋势")
        assert chart_type.name == "折线图"
        assert chart_type.description == "用于展示趋势"
        assert chart_type.is_active == True

    def test_create_real(self):
        data = ChartType(
            name="Test ChartType 1",
            description="ABC-123"
        )
        test_chart_type_dao = ChartTypeDAO()
        obj = test_chart_type_dao.create(data)

        assert obj.name == data.name
        assert obj.description == data.description

    def test_get_by_name(self, dao, setup_database):
        # 创建测试数据
        dao.create(name="柱状图", description="用于比较数据")

        # 测试获取
        chart_type = dao.get_by_name("柱状图")
        assert chart_type is not None
        assert chart_type.name == "柱状图"

        # 测试获取不存在的数据
        non_existent = dao.get_by_name("不存在的榜单")
        assert non_existent is None

    def test_get_all_active(self, dao, setup_database):
        # 创建测试数据
        dao.create(name="折线图", is_active=True)
        dao.create(name="柱状图", is_active=True)
        dao.create(name="饼图", is_active=False)

        active_types = dao.get_all_active()
        assert len(active_types) == 2
        assert all(ct.is_active for ct in active_types)

    def test_update(self, dao, setup_database):
        # 创建测试数据
        chart_type = dao.create(name="旧名称", description="旧描述")

        # 更新数据
        updated = dao.update(
            chart_type_id=chart_type.id,
            name="新名称",
            description="新描述",
            is_active=False
        )

        assert updated is not None
        assert updated.name == "新名称"
        assert updated.description == "新描述"
        assert updated.is_active == False

        # 测试更新不存在的数据
        non_existent = dao.update(chart_type_id=9999, name="测试")
        assert non_existent is None

    def test_partial_update(self, dao, setup_database):
        chart_type = dao.create(name="测试榜单", description="测试描述")

        # 只更新名称
        updated = dao.update(chart_type_id=chart_type.id, name="新名称")
        assert updated.name == "新名称"
        assert updated.description == "测试描述"  # 描述保持不变
        assert updated.is_active == True  # 激活状态保持不变


if __name__ == "__main__":
    pytest.main(["-v"])
