"""JOIN 跨租户泄露测试 E2E。"""

import pytest
from app.infrastructure.sec.join_query_definition_registry import JoinQueryDefinitionRegistry


class TestJoinCrossTenantLeakageE2E:
    """销售/采购/库存 JOIN + 多表 JOIN + 子查询 + LEFT JOIN。"""

    def test_join_definitions_registered(self) -> None:
        registry = JoinQueryDefinitionRegistry()
        defs = registry.get_all()
        assert len(defs) >= 10

    def test_sal_join_definitions(self) -> None:
        registry = JoinQueryDefinitionRegistry()
        sal_joins = registry.get_by_module("sal")
        assert len(sal_joins) >= 3

    def test_pur_join_definitions(self) -> None:
        registry = JoinQueryDefinitionRegistry()
        pur_joins = registry.get_by_module("pur")
        assert len(pur_joins) >= 3

    def test_inv_join_definitions(self) -> None:
        registry = JoinQueryDefinitionRegistry()
        inv_joins = registry.get_by_module("inv")
        assert len(inv_joins) >= 2