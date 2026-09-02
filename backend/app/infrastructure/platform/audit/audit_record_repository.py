"""审计仓储实现。"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select, insert, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.platform.audit.aggregates.audit_record_aggregate import AuditRecordAggregate


class AuditRecordRepository:
    """审计记录仓储 - 仅 INSERT，无 update/delete。"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, record: AuditRecordAggregate) -> None:
        await self._session.execute(
            insert(
                text(
                    "INSERT INTO plt_audit_record "
                    "(audit_id, tenant_id, module, aggregate_root_type, aggregate_root_id, "
                    "operation_type, operator_id, before_snapshot, after_snapshot, trace_id, "
                    "timestamp, prev_hash, record_hash, retention_until, immutable) "
                    "VALUES (:audit_id, :tenant_id, :module, :aggregate_root_type, :aggregate_root_id, "
                    ":operation_type, :operator_id, :before_snapshot, :after_snapshot, :trace_id, "
                    ":timestamp, :prev_hash, :record_hash, :retention_until, true)"
                )
            ),
            {
                "audit_id": str(record.audit_id),
                "tenant_id": str(record.tenant_id),
                "module": record.module,
                "aggregate_root_type": record.aggregate_root_type,
                "aggregate_root_id": record.aggregate_root_id,
                "operation_type": record.operation_type,
                "operator_id": record.operator_id,
                "before_snapshot": record.before_snapshot,
                "after_snapshot": record.after_snapshot,
                "trace_id": record.trace_id,
                "timestamp": record.timestamp,
                "prev_hash": record.prev_hash,
                "record_hash": record.record_hash,
                "retention_until": record.retention_until,
            },
        )

    async def get_by_id(self, audit_id: UUID) -> dict | None:
        result = await self._session.execute(
            text("SELECT * FROM plt_audit_record WHERE audit_id = :audit_id"),
            {"audit_id": str(audit_id)},
        )
        row = result.first()
        return dict(row._mapping) if row else None

    async def get_prev_hash(self, tenant_id: UUID) -> str:
        from app.domain.platform.audit.aggregates.audit_record_aggregate import compute_genesis_hash

        result = await self._session.execute(
            text(
                "SELECT record_hash FROM plt_audit_record "
                "WHERE tenant_id = :tenant_id ORDER BY timestamp DESC LIMIT 1"
            ),
            {"tenant_id": str(tenant_id)},
        )
        row = result.first()
        return row[0] if row else compute_genesis_hash()

    async def query_multi_dim(
        self,
        tenant_id: UUID | None = None,
        module: str | None = None,
        operation_type: str | None = None,
        operator_id: str | None = None,
        aggregate_root_type: str | None = None,
        aggregate_root_id: str | None = None,
        trace_id: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict]:
        conditions = []
        params: dict[str, Any] = {}

        if tenant_id is not None:
            conditions.append("tenant_id = :tenant_id")
            params["tenant_id"] = str(tenant_id)
        if module is not None:
            conditions.append("module = :module")
            params["module"] = module
        if operation_type is not None:
            conditions.append("operation_type = :operation_type")
            params["operation_type"] = operation_type
        if operator_id is not None:
            conditions.append("operator_id = :operator_id")
            params["operator_id"] = operator_id
        if aggregate_root_type is not None:
            conditions.append("aggregate_root_type = :aggregate_root_type")
            params["aggregate_root_type"] = aggregate_root_type
        if aggregate_root_id is not None:
            conditions.append("aggregate_root_id = :aggregate_root_id")
            params["aggregate_root_id"] = aggregate_root_id
        if trace_id is not None:
            conditions.append("trace_id = :trace_id")
            params["trace_id"] = trace_id
        if start_time is not None:
            conditions.append("timestamp >= :start_time")
            params["start_time"] = start_time
        if end_time is not None:
            conditions.append("timestamp <= :end_time")
            params["end_time"] = end_time

        where_clause = " AND ".join(conditions) if conditions else "1=1"
        params["limit"] = limit
        params["offset"] = offset

        result = await self._session.execute(
            text(
                f"SELECT * FROM plt_audit_record WHERE {where_clause} "
                f"ORDER BY timestamp DESC LIMIT :limit OFFSET :offset"
            ),
            params,
        )
        return [dict(row._mapping) for row in result.fetchall()]

    async def get_chain_for_tenant(
        self,
        tenant_id: UUID,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> list[dict]:
        conditions = ["tenant_id = :tenant_id"]
        params: dict[str, Any] = {"tenant_id": str(tenant_id)}

        if start_time is not None:
            conditions.append("timestamp >= :start_time")
            params["start_time"] = start_time
        if end_time is not None:
            conditions.append("timestamp <= :end_time")
            params["end_time"] = end_time

        where_clause = " AND ".join(conditions)
        result = await self._session.execute(
            text(
                f"SELECT * FROM plt_audit_record WHERE {where_clause} ORDER BY timestamp ASC"
            ),
            params,
        )
        return [dict(row._mapping) for row in result.fetchall()]

