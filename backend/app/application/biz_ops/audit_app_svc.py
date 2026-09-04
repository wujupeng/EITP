"""AuditAppSvc - 审计查询应用服务。"""

from __future__ import annotations

import json
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.biz_ops.models import BizOpsOperationAuditORM


class AuditAppSvc:
    """审计查询应用服务 - 按 DataScope 收敛查询。"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def query_operations(
        self,
        tenant_id: UUID,
        operation_type: str | None = None,
        entity_type: str | None = None,
        entity_id: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        stmt = select(BizOpsOperationAuditORM).where(BizOpsOperationAuditORM.tenant_id == tenant_id)
        if operation_type:
            stmt = stmt.where(BizOpsOperationAuditORM.operation_type == operation_type)
        if entity_type:
            stmt = stmt.where(BizOpsOperationAuditORM.entity_type == entity_type)
        if entity_id:
            stmt = stmt.where(BizOpsOperationAuditORM.entity_id == UUID(entity_id))

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await self._session.execute(count_stmt)).scalar() or 0

        stmt = stmt.order_by(BizOpsOperationAuditORM.occurred_at.desc())
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        orm_list = list((await self._session.execute(stmt)).scalars().all())

        return {
            "items": [self._orm_to_dict(o) for o in orm_list],
            "total": total, "page": page, "page_size": page_size,
        }

    async def query_by_trace(self, tenant_id: UUID, trace_id: str) -> dict | None:
        stmt = select(BizOpsOperationAuditORM).where(
            BizOpsOperationAuditORM.tenant_id == tenant_id,
            BizOpsOperationAuditORM.trace_id == trace_id,
        )
        orm = (await self._session.execute(stmt)).scalar_one_or_none()
        return self._orm_to_dict(orm) if orm else None

    def _orm_to_dict(self, orm: BizOpsOperationAuditORM) -> dict:
        return {
            "id": str(orm.id), "tenant_id": str(orm.tenant_id),
            "trace_id": orm.trace_id, "operation_type": orm.operation_type,
            "operator_id": str(orm.operator_id), "entity_type": orm.entity_type,
            "entity_id": str(orm.entity_id), "occurred_at": orm.occurred_at.isoformat(),
            "audit_data": json.loads(orm.audit_data) if orm.audit_data else {},
        }