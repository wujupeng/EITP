"""DataScopeRepository - 数据权限持久化。"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.authz.aggregates.data_scope_aggregate import (
    DataScopeAggregate,
    ScopeType,
    AccessMode,
)


class DataScopeRepository:
    """数据权限仓储。"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_role(self, role_id: UUID) -> DataScopeAggregate | None:
        result = await self._session.execute(
            text("SELECT id, role_id, scope_type, access_mode FROM iam_data_scope WHERE role_id = :rid"),
            {"rid": str(role_id)},
        )
        row = result.fetchone()
        if row is None:
            return None
        org_result = await self._session.execute(
            text("SELECT org_node_id FROM iam_data_scope_org WHERE scope_id = :sid"),
            {"sid": str(row[0])},
        )
        wh_result = await self._session.execute(
            text("SELECT warehouse_id FROM iam_data_scope_warehouse WHERE scope_id = :sid"),
            {"sid": str(row[0])},
        )
        return DataScopeAggregate(
            id=row[0],
            role_id=row[1],
            scope_type=ScopeType(row[2]),
            access_mode=AccessMode(row[3]),
            org_ids={r[0] for r in org_result.fetchall()},
            warehouse_ids={r[0] for r in wh_result.fetchall()},
        )

    async def save(self, scope: DataScopeAggregate) -> DataScopeAggregate:
        await self._session.execute(
            text(
                "INSERT INTO iam_data_scope (id, role_id, scope_type, access_mode) "
                "VALUES (:id, :rid, :st, :am) ON CONFLICT DO NOTHING"
            ),
            {"id": str(scope.id), "rid": str(scope.role_id), "st": scope.scope_type.value, "am": scope.access_mode.value},
        )
        for oid in scope.org_ids:
            await self._session.execute(
                text("INSERT INTO iam_data_scope_org (scope_id, org_node_id) VALUES (:sid, :oid) ON CONFLICT DO NOTHING"),
                {"sid": str(scope.id), "oid": str(oid)},
            )
        for wid in scope.warehouse_ids:
            await self._session.execute(
                text("INSERT INTO iam_data_scope_warehouse (scope_id, warehouse_id) VALUES (:sid, :wid) ON CONFLICT DO NOTHING"),
                {"sid": str(scope.id), "wid": str(wid)},
            )
        await self._session.flush()
        return scope