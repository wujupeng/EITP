"""TenantFilterEvent - 仓储层租户隔离核心。

对所有标记 TenantScopedMixin 的 ORM 实体，在查询编译前自动追加
WHERE tenant_id = :ctx_tenant_id，实现仓储层纵深隔离。
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import event
from sqlalchemy.orm import Session
from sqlalchemy.orm.query import Query
from sqlalchemy.sql import Select, select

from app.infrastructure.db.base import TenantScopedMixin

_TENANT_FILTER_ENABLED = True


def get_tenant_id_from_context() -> Any:
    """从当前请求上下文获取 tenant_id。

    由 TenantContextMiddleware 在请求开始时设置。
    若上下文中无 tenant_id 且处于严格模式，抛出 RuntimeError。
    """
    from app.interfaces.middleware.tenant_context import TenantContext

    ctx = TenantContext.current()
    if ctx is None:
        raise RuntimeError(
            "TenantFilterEvent: 请求上下文中无 TenantContext，"
            "仓储层查询被拒绝（严格模式）。"
        )
    return ctx.tenant_id


def _apply_tenant_filter(query: Any) -> Any:
    """对查询追加 tenant_id 过滤条件。"""
    if not _TENANT_FILTER_ENABLED:
        return query

    tenant_id = get_tenant_id_from_context()

    if isinstance(query, Select):
        entities = [
            col.class_
            for col in query.column_descriptions
            if col.get("entity") is not None
        ]
        for entity_cls in entities:
            if isinstance(entity_cls, type) and issubclass(entity_cls, TenantScopedMixin):
                if hasattr(entity_cls, "tenant_id"):
                    query = query.where(entity_cls.tenant_id == tenant_id)
    return query


@event.listens_for(Query, "before_compile", retval=True)
def _before_compile_orm(query: Query) -> Query:
    return _apply_tenant_filter(query)


def enable_tenant_filter() -> None:
    global _TENANT_FILTER_ENABLED
    _TENANT_FILTER_ENABLED = True


def disable_tenant_filter() -> None:
    global _TENANT_FILTER_ENABLED
    _TENANT_FILTER_ENABLED = False