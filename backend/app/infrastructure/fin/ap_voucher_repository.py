"""FIN 应付凭证仓储 - APVoucherRepository。"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.fin.aggregates.ap_voucher_aggregate import APVoucherAggregate
from app.domain.fin.value_objects.enums import VoucherStatus
from app.domain.fin.value_objects.money import Money


class APVoucherRepository:
    """应付凭证仓储 - upsert + 多维查询。"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, voucher: APVoucherAggregate) -> None:
        await self._session.execute(
            text(
                "INSERT INTO fin_ap_voucher "
                "(voucher_id, tenant_id, voucher_no, business_ref_type, business_ref_id, "
                "payable_amount, paid_amount, unpaid_amount, status, "
                "payment_terms, due_date, is_overdue, overdue_days, "
                "created_at, updated_at) "
                "VALUES (:voucher_id, :tenant_id, :voucher_no, :business_ref_type, :business_ref_id, "
                ":payable_amount, :paid_amount, :unpaid_amount, :status, "
                ":payment_terms, :due_date, :is_overdue, :overdue_days, "
                ":created_at, :updated_at) "
                "ON CONFLICT (voucher_no) DO UPDATE SET "
                "payable_amount = EXCLUDED.payable_amount, "
                "paid_amount = EXCLUDED.paid_amount, "
                "unpaid_amount = EXCLUDED.unpaid_amount, "
                "status = EXCLUDED.status, "
                "payment_terms = EXCLUDED.payment_terms, "
                "due_date = EXCLUDED.due_date, "
                "is_overdue = EXCLUDED.is_overdue, "
                "overdue_days = EXCLUDED.overdue_days, "
                "updated_at = EXCLUDED.updated_at"
            ),
            self._to_params(voucher),
        )

    def _to_params(self, voucher: APVoucherAggregate) -> dict[str, Any]:
        return {
            "voucher_id": str(voucher.voucher_id),
            "tenant_id": str(voucher.tenant_id),
            "voucher_no": voucher.voucher_no,
            "business_ref_type": voucher.business_ref_type,
            "business_ref_id": voucher.business_ref_id,
            "payable_amount": voucher.payable_amount.amount,
            "paid_amount": voucher.paid_amount.amount,
            "unpaid_amount": voucher.unpaid_amount.amount,
            "status": voucher.status.value,
            "payment_terms": voucher.payment_terms,
            "due_date": voucher.due_date,
            "is_overdue": voucher.is_overdue,
            "overdue_days": voucher.overdue_days,
            "created_at": voucher.created_at,
            "updated_at": voucher.updated_at,
        }

    async def get_by_id(self, voucher_id: UUID) -> APVoucherAggregate | None:
        result = await self._session.execute(
            text("SELECT * FROM fin_ap_voucher WHERE voucher_id = :voucher_id"),
            {"voucher_id": str(voucher_id)},
        )
        row = result.first()
        return self._to_aggregate(dict(row._mapping)) if row else None

    async def get_by_no(self, voucher_no: str) -> APVoucherAggregate | None:
        result = await self._session.execute(
            text("SELECT * FROM fin_ap_voucher WHERE voucher_no = :voucher_no"),
            {"voucher_no": voucher_no},
        )
        row = result.first()
        return self._to_aggregate(dict(row._mapping)) if row else None

    async def list_ap_vouchers(
        self,
        tenant_id: UUID,
        status: str | None = None,
        is_overdue: bool | None = None,
        business_ref_type: str | None = None,
        business_ref_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[APVoucherAggregate]:
        conditions: list[str] = ["tenant_id = :tenant_id"]
        params: dict[str, Any] = {"tenant_id": str(tenant_id)}
        if status is not None:
            conditions.append("status = :status")
            params["status"] = status
        if is_overdue is not None:
            conditions.append("is_overdue = :is_overdue")
            params["is_overdue"] = is_overdue
        if business_ref_type is not None:
            conditions.append("business_ref_type = :business_ref_type")
            params["business_ref_type"] = business_ref_type
        if business_ref_id is not None:
            conditions.append("business_ref_id = :business_ref_id")
            params["business_ref_id"] = business_ref_id
        where_clause = " AND ".join(conditions)
        params["limit"] = limit
        params["offset"] = offset
        result = await self._session.execute(
            text(
                f"SELECT * FROM fin_ap_voucher WHERE {where_clause} "
                f"ORDER BY created_at DESC LIMIT :limit OFFSET :offset"
            ),
            params,
        )
        return [self._to_aggregate(dict(row._mapping)) for row in result.fetchall()]

    async def update_status(
        self, voucher_id: UUID, status: VoucherStatus
    ) -> None:
        await self._session.execute(
            text(
                "UPDATE fin_ap_voucher SET status = :status, updated_at = now() "
                "WHERE voucher_id = :voucher_id"
            ),
            {"voucher_id": str(voucher_id), "status": status.value},
        )

    def _to_aggregate(self, d: dict) -> APVoucherAggregate:
        return APVoucherAggregate(
            voucher_id=UUID(str(d["voucher_id"])),
            voucher_no=d["voucher_no"],
            business_ref_type=d["business_ref_type"],
            business_ref_id=d["business_ref_id"],
            payable_amount=Money(Decimal(str(d["payable_amount"]))),
            paid_amount=Money(Decimal(str(d["paid_amount"]))),
            unpaid_amount=Money(Decimal(str(d["unpaid_amount"]))),
            status=VoucherStatus(d["status"]),
            payment_terms=d.get("payment_terms"),
            due_date=d.get("due_date"),
            is_overdue=d["is_overdue"],
            overdue_days=d["overdue_days"],
            tenant_id=UUID(str(d["tenant_id"])),
            created_at=d.get("created_at", datetime.utcnow()),
            updated_at=d.get("updated_at", datetime.utcnow()),
        )