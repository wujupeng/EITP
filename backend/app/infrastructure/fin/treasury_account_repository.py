"""FIN 资金账户仓储 - TreasuryAccountRepository。"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.fin.aggregates.treasury_account_aggregate import (
    TreasuryAccountAggregate,
)
from app.domain.fin.value_objects.enums import TreasuryAccountType
from app.domain.fin.value_objects.money import Money


class TreasuryAccountRepository:
    """资金账户仓储 - upsert + 多维查询。"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, account: TreasuryAccountAggregate) -> None:
        await self._session.execute(
            text(
                "INSERT INTO fin_treasury_account "
                "(account_id, tenant_id, account_no, account_type, currency, "
                "balance, frozen_amount, created_at, updated_at) "
                "VALUES (:account_id, :tenant_id, :account_no, :account_type, :currency, "
                ":balance, :frozen_amount, :created_at, :updated_at) "
                "ON CONFLICT (account_no) DO UPDATE SET "
                "account_type = EXCLUDED.account_type, "
                "currency = EXCLUDED.currency, "
                "balance = EXCLUDED.balance, "
                "frozen_amount = EXCLUDED.frozen_amount, "
                "updated_at = EXCLUDED.updated_at"
            ),
            self._to_params(account),
        )

    def _to_params(self, a: TreasuryAccountAggregate) -> dict[str, Any]:
        return {
            "account_id": str(a.account_id),
            "tenant_id": str(a.tenant_id),
            "account_no": a.account_no,
            "account_type": a.account_type.value,
            "currency": a.currency,
            "balance": a.balance.amount,
            "frozen_amount": a.frozen_amount.amount,
            "created_at": a.created_at,
            "updated_at": a.updated_at,
        }

    async def get_by_id(self, account_id: UUID) -> TreasuryAccountAggregate | None:
        result = await self._session.execute(
            text("SELECT * FROM fin_treasury_account WHERE account_id = :account_id"),
            {"account_id": str(account_id)},
        )
        row = result.first()
        return self._to_aggregate(dict(row._mapping)) if row else None

    async def get_by_no(self, account_no: str) -> TreasuryAccountAggregate | None:
        result = await self._session.execute(
            text("SELECT * FROM fin_treasury_account WHERE account_no = :account_no"),
            {"account_no": account_no},
        )
        row = result.first()
        return self._to_aggregate(dict(row._mapping)) if row else None

    async def list_treasury_accounts(
        self,
        tenant_id: UUID,
        account_type: str | None = None,
        currency: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[TreasuryAccountAggregate]:
        conditions: list[str] = ["tenant_id = :tenant_id"]
        params: dict[str, Any] = {"tenant_id": str(tenant_id)}
        if account_type is not None:
            conditions.append("account_type = :account_type")
            params["account_type"] = account_type
        if currency is not None:
            conditions.append("currency = :currency")
            params["currency"] = currency
        where_clause = " AND ".join(conditions)
        params["limit"] = limit
        params["offset"] = offset
        result = await self._session.execute(
            text(
                f"SELECT * FROM fin_treasury_account WHERE {where_clause} "
                f"ORDER BY created_at DESC LIMIT :limit OFFSET :offset"
            ),
            params,
        )
        return [self._to_aggregate(dict(row._mapping)) for row in result.fetchall()]

    def _to_aggregate(self, d: dict) -> TreasuryAccountAggregate:
        return TreasuryAccountAggregate(
            account_id=UUID(str(d["account_id"])),
            account_no=d["account_no"],
            account_type=TreasuryAccountType(d["account_type"]),
            currency=d["currency"],
            balance=Money(Decimal(str(d["balance"])), d["currency"]),
            frozen_amount=Money(Decimal(str(d["frozen_amount"])), d["currency"]),
            tenant_id=UUID(str(d["tenant_id"])),
            created_at=d.get("created_at", datetime.utcnow()),
            updated_at=d.get("updated_at", datetime.utcnow()),
        )