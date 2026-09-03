"""FIN 资金调拨仓储 - TreasuryTransferRepository。"""

from __future__ import annotations

import json
from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.fin.aggregates.treasury_transfer_aggregate import (
    TreasuryTransferAggregate,
)
from app.domain.fin.value_objects.enums import TransferStatus
from app.domain.fin.value_objects.money import Money


class TreasuryTransferRepository:
    """资金调拨仓储 - upsert + 多维查询。"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, transfer: TreasuryTransferAggregate) -> None:
        await self._session.execute(
            text(
                "INSERT INTO fin_treasury_transfer "
                "(transfer_id, tenant_id, transfer_no, from_account_id, to_account_id, "
                "transfer_amount, reason, status, approver_ids, created_at, updated_at) "
                "VALUES (:transfer_id, :tenant_id, :transfer_no, :from_account_id, :to_account_id, "
                ":transfer_amount, :reason, :status, :approver_ids, :created_at, :updated_at) "
                "ON CONFLICT (transfer_no) DO UPDATE SET "
                "transfer_amount = EXCLUDED.transfer_amount, "
                "reason = EXCLUDED.reason, "
                "status = EXCLUDED.status, "
                "approver_ids = EXCLUDED.approver_ids, "
                "updated_at = EXCLUDED.updated_at"
            ),
            self._to_params(transfer),
        )

    def _to_params(self, t: TreasuryTransferAggregate) -> dict[str, Any]:
        return {
            "transfer_id": str(t.transfer_id),
            "tenant_id": str(t.tenant_id),
            "transfer_no": t.transfer_no,
            "from_account_id": str(t.from_account_id),
            "to_account_id": str(t.to_account_id),
            "transfer_amount": t.transfer_amount.amount,
            "reason": t.reason,
            "status": t.status.value,
            "approver_ids": json.dumps(list(t.approver_ids)),
            "created_at": t.created_at,
            "updated_at": t.updated_at,
        }

    async def get_by_id(self, transfer_id: UUID) -> TreasuryTransferAggregate | None:
        result = await self._session.execute(
            text("SELECT * FROM fin_treasury_transfer WHERE transfer_id = :transfer_id"),
            {"transfer_id": str(transfer_id)},
        )
        row = result.first()
        return self._to_aggregate(dict(row._mapping)) if row else None

    async def get_by_no(self, transfer_no: str) -> TreasuryTransferAggregate | None:
        result = await self._session.execute(
            text("SELECT * FROM fin_treasury_transfer WHERE transfer_no = :transfer_no"),
            {"transfer_no": transfer_no},
        )
        row = result.first()
        return self._to_aggregate(dict(row._mapping)) if row else None

    async def list_transfers(
        self,
        tenant_id: UUID,
        status: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[TreasuryTransferAggregate]:
        conditions: list[str] = ["tenant_id = :tenant_id"]
        params: dict[str, Any] = {"tenant_id": str(tenant_id)}
        if status is not None:
            conditions.append("status = :status")
            params["status"] = status
        where_clause = " AND ".join(conditions)
        params["limit"] = limit
        params["offset"] = offset
        result = await self._session.execute(
            text(
                f"SELECT * FROM fin_treasury_transfer WHERE {where_clause} "
                f"ORDER BY created_at DESC LIMIT :limit OFFSET :offset"
            ),
            params,
        )
        return [self._to_aggregate(dict(row._mapping)) for row in result.fetchall()]

    def _to_aggregate(self, d: dict) -> TreasuryTransferAggregate:
        approver_ids = tuple(json.loads(d["approver_ids"])) if d.get("approver_ids") else ()
        currency = "CNY"
        return TreasuryTransferAggregate(
            transfer_id=UUID(str(d["transfer_id"])),
            transfer_no=d["transfer_no"],
            from_account_id=UUID(str(d["from_account_id"])),
            to_account_id=UUID(str(d["to_account_id"])),
            transfer_amount=Money(Decimal(str(d["transfer_amount"])), currency),
            reason=d["reason"],
            status=TransferStatus(d["status"]),
            approver_ids=approver_ids,
            tenant_id=UUID(str(d["tenant_id"])),
            created_at=d.get("created_at", datetime.utcnow()),
            updated_at=d.get("updated_at", datetime.utcnow()),
        )