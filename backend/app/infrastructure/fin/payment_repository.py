"""FIN 付款仓储 - PaymentRepository。"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.fin.aggregates.payment_aggregate import PaymentAggregate
from app.domain.fin.value_objects.enums import PaymentMethod, PaymentStatus
from app.domain.fin.value_objects.money import Money


class PaymentRepository:
    """付款仓储 - upsert + 多维查询。"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, payment: PaymentAggregate) -> None:
        await self._session.execute(
            text(
                "INSERT INTO fin_payment "
                "(payment_id, tenant_id, payment_no, ap_voucher_no, "
                "payment_amount, payment_method, payment_account, payee_account, "
                "status, approver_id, approval_opinion, bank_ref, "
                "expected_payment_date, actual_payment_date, created_at, updated_at) "
                "VALUES (:payment_id, :tenant_id, :payment_no, :ap_voucher_no, "
                ":payment_amount, :payment_method, :payment_account, :payee_account, "
                ":status, :approver_id, :approval_opinion, :bank_ref, "
                ":expected_payment_date, :actual_payment_date, :created_at, :updated_at) "
                "ON CONFLICT (payment_no) DO UPDATE SET "
                "payment_amount = EXCLUDED.payment_amount, "
                "payment_method = EXCLUDED.payment_method, "
                "payment_account = EXCLUDED.payment_account, "
                "payee_account = EXCLUDED.payee_account, "
                "status = EXCLUDED.status, "
                "approver_id = EXCLUDED.approver_id, "
                "approval_opinion = EXCLUDED.approval_opinion, "
                "bank_ref = EXCLUDED.bank_ref, "
                "expected_payment_date = EXCLUDED.expected_payment_date, "
                "actual_payment_date = EXCLUDED.actual_payment_date, "
                "updated_at = EXCLUDED.updated_at"
            ),
            self._to_params(payment),
        )

    def _to_params(self, p: PaymentAggregate) -> dict[str, Any]:
        return {
            "payment_id": str(p.payment_id),
            "tenant_id": str(p.tenant_id),
            "payment_no": p.payment_no,
            "ap_voucher_no": p.ap_voucher_no,
            "payment_amount": p.payment_amount.amount,
            "payment_method": p.payment_method.value,
            "payment_account": p.payment_account,
            "payee_account": p.payee_account,
            "status": p.status.value,
            "approver_id": p.approver_id,
            "approval_opinion": p.approval_opinion,
            "bank_ref": p.bank_ref,
            "expected_payment_date": p.expected_payment_date,
            "actual_payment_date": p.actual_payment_date,
            "created_at": p.created_at,
            "updated_at": p.updated_at,
        }

    async def get_by_id(self, payment_id: UUID) -> PaymentAggregate | None:
        result = await self._session.execute(
            text("SELECT * FROM fin_payment WHERE payment_id = :payment_id"),
            {"payment_id": str(payment_id)},
        )
        row = result.first()
        return self._to_aggregate(dict(row._mapping)) if row else None

    async def get_by_no(self, payment_no: str) -> PaymentAggregate | None:
        result = await self._session.execute(
            text("SELECT * FROM fin_payment WHERE payment_no = :payment_no"),
            {"payment_no": payment_no},
        )
        row = result.first()
        return self._to_aggregate(dict(row._mapping)) if row else None

    async def get_by_bank_ref(self, bank_ref: str) -> PaymentAggregate | None:
        result = await self._session.execute(
            text("SELECT * FROM fin_payment WHERE bank_ref = :bank_ref"),
            {"bank_ref": bank_ref},
        )
        row = result.first()
        return self._to_aggregate(dict(row._mapping)) if row else None

    async def list_payments(
        self,
        tenant_id: UUID,
        status: str | None = None,
        ap_voucher_no: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[PaymentAggregate]:
        conditions: list[str] = ["tenant_id = :tenant_id"]
        params: dict[str, Any] = {"tenant_id": str(tenant_id)}
        if status is not None:
            conditions.append("status = :status")
            params["status"] = status
        if ap_voucher_no is not None:
            conditions.append("ap_voucher_no = :ap_voucher_no")
            params["ap_voucher_no"] = ap_voucher_no
        where_clause = " AND ".join(conditions)
        params["limit"] = limit
        params["offset"] = offset
        result = await self._session.execute(
            text(
                f"SELECT * FROM fin_payment WHERE {where_clause} "
                f"ORDER BY created_at DESC LIMIT :limit OFFSET :offset"
            ),
            params,
        )
        return [self._to_aggregate(dict(row._mapping)) for row in result.fetchall()]

    async def update_status(
        self, payment_id: UUID, status: PaymentStatus
    ) -> None:
        await self._session.execute(
            text(
                "UPDATE fin_payment SET status = :status, updated_at = now() "
                "WHERE payment_id = :payment_id"
            ),
            {"payment_id": str(payment_id), "status": status.value},
        )

    def _to_aggregate(self, d: dict) -> PaymentAggregate:
        return PaymentAggregate(
            payment_id=UUID(str(d["payment_id"])),
            payment_no=d["payment_no"],
            ap_voucher_no=d["ap_voucher_no"],
            payment_amount=Money(Decimal(str(d["payment_amount"]))),
            payment_method=PaymentMethod(d["payment_method"]),
            payment_account=d["payment_account"],
            payee_account=d["payee_account"],
            status=PaymentStatus(d["status"]),
            approver_id=d.get("approver_id"),
            approval_opinion=d.get("approval_opinion"),
            bank_ref=d.get("bank_ref"),
            expected_payment_date=d.get("expected_payment_date"),
            actual_payment_date=d.get("actual_payment_date"),
            tenant_id=UUID(str(d["tenant_id"])),
            created_at=d.get("created_at", datetime.utcnow()),
            updated_at=d.get("updated_at", datetime.utcnow()),
        )