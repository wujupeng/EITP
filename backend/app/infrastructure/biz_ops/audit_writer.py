"""AuditWriter - 审计写入器，append-only 独立事务。"""

from __future__ import annotations

import json
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.domain.biz_ops.aggregates.operation_audit_aggregate import OperationAuditAggregate
from app.infrastructure.biz_ops.models import BizOpsOperationAuditORM


class AuditWriter:
    """审计写入器 - append-only，异步写入不阻塞主操作。"""

    async def write(self, session: AsyncSession, agg: OperationAuditAggregate) -> BizOpsOperationAuditORM:
        """同步写入审计记录（在主事务中调用）。"""
        orm = BizOpsOperationAuditORM(
            id=agg.id.value, tenant_id=agg.tenant_id, trace_id=agg.trace_id,
            operation_type=agg.operation_type.value, operator_id=agg.operator_id,
            entity_type=agg.entity_type, entity_id=agg.entity_id,
            occurred_at=agg.occurred_at, audit_data=json.dumps(agg.to_dict(), ensure_ascii=False, default=str),
        )
        session.add(orm)
        await session.flush()
        return orm

    async def write_async(self, session_factory: async_sessionmaker, agg: OperationAuditAggregate) -> None:
        """异步写入审计记录（独立事务，不阻塞主操作）。"""
        async with session_factory() as audit_session:
            await self.write(audit_session, agg)
            await audit_session.commit()