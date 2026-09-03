"""FIN 催收任务仓储 - CollectionTaskRepository。"""

from __future__ import annotations

import json
from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.fin.aggregates.collection_task_aggregate import (
    CollectionRecord,
    CollectionTaskAggregate,
)
from app.domain.fin.value_objects.enums import (
    CollectionStage,
    CollectionTaskStatus,
)
from app.domain.fin.value_objects.money import Money


class CollectionTaskRepository:
    """催收任务仓储 - upsert + 多维查询。"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, task: CollectionTaskAggregate) -> None:
        await self._session.execute(
            text(
                "INSERT INTO fin_collection_task "
                "(task_id, tenant_id, ar_voucher_no, overdue_amount, overdue_days, "
                "collection_stage, status, records, created_at, updated_at) "
                "VALUES (:task_id, :tenant_id, :ar_voucher_no, :overdue_amount, :overdue_days, "
                ":collection_stage, :status, :records, :created_at, :updated_at) "
                "ON CONFLICT (task_id) DO UPDATE SET "
                "overdue_amount = EXCLUDED.overdue_amount, "
                "overdue_days = EXCLUDED.overdue_days, "
                "collection_stage = EXCLUDED.collection_stage, "
                "status = EXCLUDED.status, "
                "records = EXCLUDED.records, "
                "updated_at = EXCLUDED.updated_at"
            ),
            self._to_params(task),
        )

    def _to_params(self, t: CollectionTaskAggregate) -> dict[str, Any]:
        return {
            "task_id": str(t.task_id),
            "tenant_id": str(t.tenant_id),
            "ar_voucher_no": t.ar_voucher_no,
            "overdue_amount": t.overdue_amount.amount,
            "overdue_days": t.overdue_days,
            "collection_stage": t.collection_stage.value,
            "status": t.status.value,
            "records": json.dumps(
                [
                    {
                        "record_id": str(r.record_id),
                        "stage": r.stage.value,
                        "handler_id": r.handler_id,
                        "content": r.content,
                        "created_at": r.created_at.isoformat(),
                    }
                    for r in t.records
                ]
            ),
            "created_at": t.created_at,
            "updated_at": t.updated_at,
        }

    async def get_by_id(self, task_id: UUID) -> CollectionTaskAggregate | None:
        result = await self._session.execute(
            text("SELECT * FROM fin_collection_task WHERE task_id = :task_id"),
            {"task_id": str(task_id)},
        )
        row = result.first()
        return self._to_aggregate(dict(row._mapping)) if row else None

    async def get_by_ar_voucher_no(
        self, ar_voucher_no: str
    ) -> CollectionTaskAggregate | None:
        result = await self._session.execute(
            text(
                "SELECT * FROM fin_collection_task WHERE ar_voucher_no = :ar_voucher_no "
                "ORDER BY created_at DESC LIMIT 1"
            ),
            {"ar_voucher_no": ar_voucher_no},
        )
        row = result.first()
        return self._to_aggregate(dict(row._mapping)) if row else None

    async def list_tasks(
        self,
        tenant_id: UUID,
        status: str | None = None,
        stage: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[CollectionTaskAggregate]:
        conditions: list[str] = ["tenant_id = :tenant_id"]
        params: dict[str, Any] = {"tenant_id": str(tenant_id)}
        if status is not None:
            conditions.append("status = :status")
            params["status"] = status
        if stage is not None:
            conditions.append("collection_stage = :stage")
            params["stage"] = stage
        where_clause = " AND ".join(conditions)
        params["limit"] = limit
        params["offset"] = offset
        result = await self._session.execute(
            text(
                f"SELECT * FROM fin_collection_task WHERE {where_clause} "
                f"ORDER BY created_at DESC LIMIT :limit OFFSET :offset"
            ),
            params,
        )
        return [self._to_aggregate(dict(row._mapping)) for row in result.fetchall()]

    def _to_aggregate(self, d: dict) -> CollectionTaskAggregate:
        records_data = json.loads(d["records"]) if d.get("records") else []
        records = tuple(
            CollectionRecord(
                record_id=UUID(str(r["record_id"])),
                stage=CollectionStage(r["stage"]),
                handler_id=r["handler_id"],
                content=r["content"],
                created_at=datetime.fromisoformat(r["created_at"]),
            )
            for r in records_data
        )
        return CollectionTaskAggregate(
            task_id=UUID(str(d["task_id"])),
            ar_voucher_no=d["ar_voucher_no"],
            overdue_amount=Money(Decimal(str(d["overdue_amount"]))),
            overdue_days=d["overdue_days"],
            collection_stage=CollectionStage(d["collection_stage"]),
            status=CollectionTaskStatus(d["status"]),
            records=records,
            tenant_id=UUID(str(d["tenant_id"])),
            created_at=d.get("created_at", datetime.utcnow()),
            updated_at=d.get("updated_at", datetime.utcnow()),
        )