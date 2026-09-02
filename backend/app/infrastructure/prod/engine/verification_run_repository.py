"""验证执行仓储 - 仅 INSERT，无 update/delete。"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.prod.engine.aggregates.verification_run_aggregate import (
    EvidenceRecord,
    VerificationRunAggregate,
)


class VerificationRunRepository:
    """验证执行记录仓储 - append-only。"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, run: VerificationRunAggregate) -> None:
        await self._session.execute(
            text(
                "INSERT INTO prod_verification_run "
                "(run_id, tenant_id, verification_item, executor, environment, "
                "status, started_at, finished_at, config_snapshot, conclusion, "
                "evidence_report_path, evidence_metrics_snapshot_path, evidence_log_path, "
                "evidence_hash, trace_id, failure_detail, created_at) "
                "VALUES (:run_id, :tenant_id, :verification_item, :executor, :environment, "
                ":status, :started_at, :finished_at, :config_snapshot, :conclusion, "
                ":evidence_report_path, :evidence_metrics_snapshot_path, :evidence_log_path, "
                ":evidence_hash, :trace_id, :failure_detail, :created_at)"
            ),
            {
                "run_id": str(run.run_id),
                "tenant_id": str(run.tenant_id),
                "verification_item": run.verification_item.value,
                "executor": run.executor.value,
                "environment": run.environment.value,
                "status": run.status.value,
                "started_at": run.started_at,
                "finished_at": run.finished_at,
                "config_snapshot": run.config_snapshot,
                "conclusion": run.conclusion.value if run.conclusion else None,
                "evidence_report_path": run.evidence_report_path,
                "evidence_metrics_snapshot_path": run.evidence_metrics_snapshot_path,
                "evidence_log_path": run.evidence_log_path,
                "evidence_hash": run.evidence_hash,
                "trace_id": run.trace_id,
                "failure_detail": run.failure_detail,
                "created_at": run.created_at,
            },
        )

    async def get_by_id(self, run_id: UUID) -> dict | None:
        result = await self._session.execute(
            text("SELECT * FROM prod_verification_run WHERE run_id = :run_id"),
            {"run_id": str(run_id)},
        )
        row = result.first()
        return dict(row._mapping) if row else None

    async def list_runs(
        self,
        tenant_id: UUID | None = None,
        verification_item: str | None = None,
        conclusion: str | None = None,
        executor: str | None = None,
        environment: str | None = None,
        status: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict]:
        conditions: list[str] = []
        params: dict[str, Any] = {}

        if tenant_id is not None:
            conditions.append("tenant_id = :tenant_id")
            params["tenant_id"] = str(tenant_id)
        if verification_item is not None:
            conditions.append("verification_item = :verification_item")
            params["verification_item"] = verification_item
        if conclusion is not None:
            conditions.append("conclusion = :conclusion")
            params["conclusion"] = conclusion
        if executor is not None:
            conditions.append("executor = :executor")
            params["executor"] = executor
        if environment is not None:
            conditions.append("environment = :environment")
            params["environment"] = environment
        if status is not None:
            conditions.append("status = :status")
            params["status"] = status
        if start_time is not None:
            conditions.append("created_at >= :start_time")
            params["start_time"] = start_time
        if end_time is not None:
            conditions.append("created_at <= :end_time")
            params["end_time"] = end_time

        where_clause = " AND ".join(conditions) if conditions else "1=1"
        params["limit"] = limit
        params["offset"] = offset

        result = await self._session.execute(
            text(
                f"SELECT * FROM prod_verification_run WHERE {where_clause} "
                f"ORDER BY created_at DESC LIMIT :limit OFFSET :offset"
            ),
            params,
        )
        return [dict(row._mapping) for row in result.fetchall()]


class EvidenceRepository:
    """证据索引仓储 - append-only。"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, evidence: EvidenceRecord) -> None:
        await self._session.execute(
            text(
                "INSERT INTO prod_verification_evidence "
                "(evidence_id, run_id, tenant_id, evidence_type, "
                "storage_path, content_hash, size_bytes, trace_id, created_at) "
                "VALUES (:evidence_id, :run_id, :tenant_id, :evidence_type, "
                ":storage_path, :content_hash, :size_bytes, :trace_id, :created_at)"
            ),
            {
                "evidence_id": str(evidence.evidence_id),
                "run_id": str(evidence.run_id),
                "tenant_id": str(evidence.tenant_id),
                "evidence_type": evidence.evidence_type,
                "storage_path": evidence.storage_path,
                "content_hash": evidence.content_hash,
                "size_bytes": evidence.size_bytes,
                "trace_id": evidence.trace_id,
                "created_at": evidence.created_at,
            },
        )

    async def get_by_run_id(self, run_id: UUID) -> list[dict]:
        result = await self._session.execute(
            text(
                "SELECT * FROM prod_verification_evidence "
                "WHERE run_id = :run_id ORDER BY created_at ASC"
            ),
            {"run_id": str(run_id)},
        )
        return [dict(row._mapping) for row in result.fetchall()]

    async def get_by_id(self, evidence_id: UUID) -> dict | None:
        result = await self._session.execute(
            text("SELECT * FROM prod_verification_evidence WHERE evidence_id = :evidence_id"),
            {"evidence_id": str(evidence_id)},
        )
        row = result.first()
        return dict(row._mapping) if row else None