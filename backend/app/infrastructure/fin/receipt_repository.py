"""FIN 收款仓储 - ReceiptRepository。"""

from __future__ import annotations

import json
from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.fin.aggregates.receipt_aggregate import (
    ReceiptAggregate,
    WriteOffLine,
)
from app.domain.fin.value_objects.enums import ReceiptStatus
from app.domain.fin.value_objects.money import Money


class ReceiptRepository:
    """收款仓储 - upsert + 多维查询。"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, receipt: ReceiptAggregate) -> None:
        await self._session.execute(
            text(
                "INSERT INTO fin_receipt "
                "(receipt_id, tenant_id, receipt_no, receipt_amount, "
                "receiver_account, payer_account, bank_ref, status, "
                "write_off_lines, arrival_time, created_at, updated_at) "
                "VALUES (:receipt_id, :tenant_id, :receipt_no, :receipt_amount, "
                ":receiver_account, :payer_account, :bank_ref, :status, "
                ":write_off_lines, :arrival_time, :created_at, :updated_at) "
                "ON CONFLICT (receipt_no) DO UPDATE SET "
                "receipt_amount = EXCLUDED.receipt_amount, "
                "receiver_account = EXCLUDED.receiver_account, "
                "payer_account = EXCLUDED.payer_account, "
                "bank_ref = EXCLUDED.bank_ref, "
                "status = EXCLUDED.status, "
                "write_off_lines = EXCLUDED.write_off_lines, "
                "arrival_time = EXCLUDED.arrival_time, "
                "updated_at = EXCLUDED.updated_at"
            ),
            self._to_params(receipt),
        )

    def _to_params(self, r: ReceiptAggregate) -> dict[str, Any]:
        return {
            "receipt_id": str(r.receipt_id),
            "tenant_id": str(r.tenant_id),
            "receipt_no": r.receipt_no,
            "receipt_amount": r.receipt_amount.amount,
            "receiver_account": r.receiver_account,
            "payer_account": r.payer_account,
            "bank_ref": r.bank_ref,
            "status": r.status.value,
            "write_off_lines": json.dumps(
                [
                    {
                        "line_no": ln.line_no,
                        "ar_voucher_no": ln.ar_voucher_no,
                        "write_off_amount": str(ln.write_off_amount.amount),
                        "currency": ln.write_off_amount.currency,
                    }
                    for ln in r.write_off_lines
                ]
            ),
            "arrival_time": r.arrival_time,
            "created_at": r.created_at,
            "updated_at": r.updated_at,
        }

    async def get_by_id(self, receipt_id: UUID) -> ReceiptAggregate | None:
        result = await self._session.execute(
            text("SELECT * FROM fin_receipt WHERE receipt_id = :receipt_id"),
            {"receipt_id": str(receipt_id)},
        )
        row = result.first()
        return self._to_aggregate(dict(row._mapping)) if row else None

    async def get_by_no(self, receipt_no: str) -> ReceiptAggregate | None:
        result = await self._session.execute(
            text("SELECT * FROM fin_receipt WHERE receipt_no = :receipt_no"),
            {"receipt_no": receipt_no},
        )
        row = result.first()
        return self._to_aggregate(dict(row._mapping)) if row else None

    async def get_by_bank_ref(self, bank_ref: str) -> ReceiptAggregate | None:
        result = await self._session.execute(
            text("SELECT * FROM fin_receipt WHERE bank_ref = :bank_ref"),
            {"bank_ref": bank_ref},
        )
        row = result.first()
        return self._to_aggregate(dict(row._mapping)) if row else None

    async def list_receipts(
        self,
        tenant_id: UUID,
        status: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[ReceiptAggregate]:
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
                f"SELECT * FROM fin_receipt WHERE {where_clause} "
                f"ORDER BY created_at DESC LIMIT :limit OFFSET :offset"
            ),
            params,
        )
        return [self._to_aggregate(dict(row._mapping)) for row in result.fetchall()]

    def _to_aggregate(self, d: dict) -> ReceiptAggregate:
        lines_data = json.loads(d["write_off_lines"]) if d.get("write_off_lines") else []
        lines = tuple(
            WriteOffLine(
                line_no=ln["line_no"],
                ar_voucher_no=ln["ar_voucher_no"],
                write_off_amount=Money(
                    Decimal(str(ln["write_off_amount"])),
                    ln.get("currency", "CNY"),
                ),
            )
            for ln in lines_data
        )
        return ReceiptAggregate(
            receipt_id=UUID(str(d["receipt_id"])),
            receipt_no=d["receipt_no"],
            receipt_amount=Money(Decimal(str(d["receipt_amount"]))),
            receiver_account=d["receiver_account"],
            payer_account=d["payer_account"],
            bank_ref=d.get("bank_ref"),
            status=ReceiptStatus(d["status"]),
            write_off_lines=lines,
            arrival_time=d.get("arrival_time"),
            tenant_id=UUID(str(d["tenant_id"])),
            created_at=d.get("created_at", datetime.utcnow()),
            updated_at=d.get("updated_at", datetime.utcnow()),
        )