"""FIN 总账凭证仓储 - GLVoucherRepository。"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.fin.aggregates.gl_voucher_aggregate import (
    GLVoucherAggregate,
    GLVoucherLine,
)
from app.domain.fin.value_objects.money import Money


class GLVoucherRepository:
    """总账凭证仓储 - 凭证+行 upsert + 期间锁定。"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, voucher: GLVoucherAggregate) -> None:
        await self._session.execute(
            text(
                "INSERT INTO fin_gl_voucher "
                "(gl_voucher_id, tenant_id, voucher_no, voucher_date, summary, "
                "business_ref_type, business_ref_id, red_original_voucher_no, "
                "period, is_period_closed, created_at, updated_at) "
                "VALUES (:gl_voucher_id, :tenant_id, :voucher_no, :voucher_date, :summary, "
                ":business_ref_type, :business_ref_id, :red_original_voucher_no, "
                ":period, :is_period_closed, :created_at, :updated_at) "
                "ON CONFLICT (tenant_id, voucher_no, period) DO UPDATE SET "
                "summary = EXCLUDED.summary, "
                "business_ref_type = EXCLUDED.business_ref_type, "
                "business_ref_id = EXCLUDED.business_ref_id, "
                "red_original_voucher_no = EXCLUDED.red_original_voucher_no, "
                "is_period_closed = EXCLUDED.is_period_closed, "
                "updated_at = EXCLUDED.updated_at"
            ),
            self._voucher_params(voucher),
        )
        await self._session.execute(
            text(
                "DELETE FROM fin_gl_voucher_line WHERE gl_voucher_id = :gl_voucher_id"
            ),
            {"gl_voucher_id": str(voucher.gl_voucher_id)},
        )
        for line in voucher.lines:
            await self._session.execute(
                text(
                    "INSERT INTO fin_gl_voucher_line "
                    "(tenant_id, gl_voucher_id, line_no, account_code, "
                    "debit_amount, credit_amount, created_at) "
                    "VALUES (:tenant_id, :gl_voucher_id, :line_no, :account_code, "
                    ":debit_amount, :credit_amount, now())"
                ),
                {
                    "tenant_id": str(voucher.tenant_id),
                    "gl_voucher_id": str(voucher.gl_voucher_id),
                    "line_no": line.line_no,
                    "account_code": line.account_code,
                    "debit_amount": line.debit_amount.amount,
                    "credit_amount": line.credit_amount.amount,
                },
            )

    def _voucher_params(self, voucher: GLVoucherAggregate) -> dict[str, Any]:
        return {
            "gl_voucher_id": str(voucher.gl_voucher_id),
            "tenant_id": str(voucher.tenant_id),
            "voucher_no": voucher.voucher_no,
            "voucher_date": voucher.voucher_date,
            "summary": voucher.summary,
            "business_ref_type": voucher.business_ref_type,
            "business_ref_id": voucher.business_ref_id,
            "red_original_voucher_no": voucher.red_original_voucher_no,
            "period": voucher.period,
            "is_period_closed": voucher.is_period_closed,
            "created_at": voucher.created_at,
            "updated_at": voucher.updated_at,
        }

    async def get_by_id(self, gl_voucher_id: UUID) -> GLVoucherAggregate | None:
        result = await self._session.execute(
            text("SELECT * FROM fin_gl_voucher WHERE gl_voucher_id = :gl_voucher_id"),
            {"gl_voucher_id": str(gl_voucher_id)},
        )
        row = result.first()
        if row is None:
            return None
        lines = await self._load_lines(UUID(str(row._mapping["gl_voucher_id"])))
        return self._to_aggregate(dict(row._mapping), lines)

    async def get_by_no(
        self, tenant_id: UUID, voucher_no: str, period: str | None = None
    ) -> GLVoucherAggregate | None:
        if period is not None:
            result = await self._session.execute(
                text(
                    "SELECT * FROM fin_gl_voucher "
                    "WHERE tenant_id = :tenant_id AND voucher_no = :voucher_no AND period = :period"
                ),
                {
                    "tenant_id": str(tenant_id),
                    "voucher_no": voucher_no,
                    "period": period,
                },
            )
        else:
            result = await self._session.execute(
                text(
                    "SELECT * FROM fin_gl_voucher "
                    "WHERE tenant_id = :tenant_id AND voucher_no = :voucher_no"
                ),
                {"tenant_id": str(tenant_id), "voucher_no": voucher_no},
            )
        row = result.first()
        if row is None:
            return None
        lines = await self._load_lines(UUID(str(row._mapping["gl_voucher_id"])))
        return self._to_aggregate(dict(row._mapping), lines)

    async def _load_lines(self, gl_voucher_id: UUID) -> list[GLVoucherLine]:
        result = await self._session.execute(
            text(
                "SELECT * FROM fin_gl_voucher_line "
                "WHERE gl_voucher_id = :gl_voucher_id ORDER BY line_no ASC"
            ),
            {"gl_voucher_id": str(gl_voucher_id)},
        )
        return [
            GLVoucherLine(
                line_no=row._mapping["line_no"],
                account_code=row._mapping["account_code"],
                debit_amount=Money(Decimal(str(row._mapping["debit_amount"]))),
                credit_amount=Money(Decimal(str(row._mapping["credit_amount"]))),
            )
            for row in result.fetchall()
        ]

    async def list_gl_vouchers(
        self,
        tenant_id: UUID,
        period: str | None = None,
        is_period_closed: bool | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[GLVoucherAggregate]:
        conditions: list[str] = ["tenant_id = :tenant_id"]
        params: dict[str, Any] = {"tenant_id": str(tenant_id)}
        if period is not None:
            conditions.append("period = :period")
            params["period"] = period
        if is_period_closed is not None:
            conditions.append("is_period_closed = :is_period_closed")
            params["is_period_closed"] = is_period_closed
        where_clause = " AND ".join(conditions)
        params["limit"] = limit
        params["offset"] = offset
        result = await self._session.execute(
            text(
                f"SELECT * FROM fin_gl_voucher WHERE {where_clause} "
                f"ORDER BY voucher_date DESC, voucher_no ASC LIMIT :limit OFFSET :offset"
            ),
            params,
        )
        vouchers: list[GLVoucherAggregate] = []
        for row in result.fetchall():
            lines = await self._load_lines(UUID(str(row._mapping["gl_voucher_id"])))
            vouchers.append(self._to_aggregate(dict(row._mapping), lines))
        return vouchers

    async def close_period(self, tenant_id: UUID, period: str) -> int:
        result = await self._session.execute(
            text(
                "UPDATE fin_gl_voucher SET is_period_closed = TRUE, updated_at = now() "
                "WHERE tenant_id = :tenant_id AND period = :period "
                "AND is_period_closed = FALSE"
            ),
            {"tenant_id": str(tenant_id), "period": period},
        )
        return result.rowcount

    def _to_aggregate(self, d: dict, lines: list[GLVoucherLine]) -> GLVoucherAggregate:
        return GLVoucherAggregate(
            gl_voucher_id=UUID(str(d["gl_voucher_id"])),
            voucher_no=d["voucher_no"],
            voucher_date=d["voucher_date"],
            summary=d.get("summary") or "",
            business_ref_type=d.get("business_ref_type"),
            business_ref_id=d.get("business_ref_id"),
            red_original_voucher_no=d.get("red_original_voucher_no"),
            period=d["period"],
            is_period_closed=d["is_period_closed"],
            lines=tuple(lines),
            tenant_id=UUID(str(d["tenant_id"])),
            created_at=d.get("created_at", datetime.utcnow()),
            updated_at=d.get("updated_at", datetime.utcnow()),
        )