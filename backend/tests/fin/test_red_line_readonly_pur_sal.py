"""红线测试 T15-8 - 只读视图：FIN 对 PUR/SAL 仅只读引用。

验证 EITP-FIN-001 的只读红线：
- PurOrderReadView / SalOrderReadView 只有查询方法，无写方法
- 查询方法执行的是 SELECT 语句，非 INSERT/UPDATE/DELETE
- 视图类位于 infrastructure 层，不在 domain 层
- 视图类不导入 PUR/SAL 聚合根
"""

from __future__ import annotations

import inspect

import pytest

from app.infrastructure.fin.pur_order_read_view import PurOrderReadView
from app.infrastructure.fin.sal_order_read_view import SalOrderReadView

# 写方法名黑名单
WRITE_METHOD_NAMES = {
    "create",
    "update",
    "delete",
    "save",
    "insert",
    "modify",
    "remove",
    "upsert",
    "bulk_create",
    "bulk_update",
    "bulk_delete",
    "add",
    "set",
    "put",
    "patch",
    "post",
}


class TestPurOrderReadViewReadOnly:
    """红线 2：PurOrderReadView 只读。"""

    def test_class_exists(self) -> None:
        assert PurOrderReadView is not None

    def test_class_in_infrastructure_layer(self) -> None:
        module = PurOrderReadView.__module__
        assert "infrastructure" in module, f"PurOrderReadView 应在 infrastructure 层，实际: {module}"
        assert "domain" not in module, "PurOrderReadView 不应在 domain 层"

    def test_has_query_method(self) -> None:
        assert hasattr(PurOrderReadView, "query")
        assert callable(getattr(PurOrderReadView, "query"))

    def test_has_get_received_quantity_method(self) -> None:
        assert hasattr(PurOrderReadView, "get_received_quantity")
        assert callable(getattr(PurOrderReadView, "get_received_quantity"))

    def test_no_write_methods(self) -> None:
        methods = {
            name
            for name, _ in inspect.getmembers(PurOrderReadView, predicate=inspect.isfunction)
        }
        forbidden = methods & WRITE_METHOD_NAMES
        assert forbidden == set(), f"PurOrderReadView 不应有写方法: {forbidden}"

    def test_query_source_is_select(self) -> None:
        source = inspect.getsource(PurOrderReadView.query)
        assert "SELECT" in source.upper()
        assert "INSERT" not in source.upper()
        assert "UPDATE" not in source.upper()
        assert "DELETE" not in source.upper()

    def test_get_received_quantity_source_is_select(self) -> None:
        source = inspect.getsource(PurOrderReadView.get_received_quantity)
        assert "SELECT" in source.upper()
        assert "INSERT" not in source.upper()
        assert "UPDATE" not in source.upper()
        assert "DELETE" not in source.upper()

    def test_does_not_import_pur_aggregate(self) -> None:
        source = inspect.getsource(PurOrderReadView)
        assert "app.domain.pur" not in source
        assert "PurOrderAggregate" not in source

    def test_uses_raw_sql_text(self) -> None:
        source = inspect.getsource(PurOrderReadView)
        assert "text(" in source, "应使用 sqlalchemy text() 执行原始 SQL"

    def test_query_targets_pur_order_table(self) -> None:
        source = inspect.getsource(PurOrderReadView.query)
        assert "pur_order" in source

    def test_get_received_quantity_targets_pur_order_line_table(self) -> None:
        source = inspect.getsource(PurOrderReadView.get_received_quantity)
        assert "pur_order_line" in source


class TestSalOrderReadViewReadOnly:
    """红线 2：SalOrderReadView 只读。"""

    def test_class_exists(self) -> None:
        assert SalOrderReadView is not None

    def test_class_in_infrastructure_layer(self) -> None:
        module = SalOrderReadView.__module__
        assert "infrastructure" in module, f"SalOrderReadView 应在 infrastructure 层，实际: {module}"
        assert "domain" not in module, "SalOrderReadView 不应在 domain 层"

    def test_has_query_method(self) -> None:
        assert hasattr(SalOrderReadView, "query")
        assert callable(getattr(SalOrderReadView, "query"))

    def test_has_get_shipped_quantity_method(self) -> None:
        assert hasattr(SalOrderReadView, "get_shipped_quantity")
        assert callable(getattr(SalOrderReadView, "get_shipped_quantity"))

    def test_no_write_methods(self) -> None:
        methods = {
            name
            for name, _ in inspect.getmembers(SalOrderReadView, predicate=inspect.isfunction)
        }
        forbidden = methods & WRITE_METHOD_NAMES
        assert forbidden == set(), f"SalOrderReadView 不应有写方法: {forbidden}"

    def test_query_source_is_select(self) -> None:
        source = inspect.getsource(SalOrderReadView.query)
        assert "SELECT" in source.upper()
        assert "INSERT" not in source.upper()
        assert "UPDATE" not in source.upper()
        assert "DELETE" not in source.upper()

    def test_get_shipped_quantity_source_is_select(self) -> None:
        source = inspect.getsource(SalOrderReadView.get_shipped_quantity)
        assert "SELECT" in source.upper()
        assert "INSERT" not in source.upper()
        assert "UPDATE" not in source.upper()
        assert "DELETE" not in source.upper()

    def test_does_not_import_sal_aggregate(self) -> None:
        source = inspect.getsource(SalOrderReadView)
        assert "app.domain.sal" not in source
        assert "SalOrderAggregate" not in source

    def test_uses_raw_sql_text(self) -> None:
        source = inspect.getsource(SalOrderReadView)
        assert "text(" in source, "应使用 sqlalchemy text() 执行原始 SQL"

    def test_query_targets_sal_order_table(self) -> None:
        source = inspect.getsource(SalOrderReadView.query)
        assert "sal_order" in source

    def test_get_shipped_quantity_targets_sal_order_line_table(self) -> None:
        source = inspect.getsource(SalOrderReadView.get_shipped_quantity)
        assert "sal_order_line" in source


class TestReadViewSymmetry:
    """红线 2：两个只读视图的结构对称性。"""

    def test_both_have_query_method(self) -> None:
        assert hasattr(PurOrderReadView, "query")
        assert hasattr(SalOrderReadView, "query")

    def test_both_have_line_quantity_method(self) -> None:
        assert hasattr(PurOrderReadView, "get_received_quantity")
        assert hasattr(SalOrderReadView, "get_shipped_quantity")

    def test_both_in_same_package(self) -> None:
        pur_pkg = PurOrderReadView.__module__.rsplit(".", 1)[0]
        sal_pkg = SalOrderReadView.__module__.rsplit(".", 1)[0]
        assert pur_pkg == sal_pkg, f"两个视图应在同一包: {pur_pkg} vs {sal_pkg}"

    def test_both_use_sqlalchemy_text(self) -> None:
        pur_src = inspect.getsource(PurOrderReadView)
        sal_src = inspect.getsource(SalOrderReadView)
        assert "text(" in pur_src
        assert "text(" in sal_src

    def test_both_use_async_session(self) -> None:
        pur_src = inspect.getsource(PurOrderReadView)
        sal_src = inspect.getsource(SalOrderReadView)
        assert "AsyncSession" in pur_src
        assert "AsyncSession" in sal_src