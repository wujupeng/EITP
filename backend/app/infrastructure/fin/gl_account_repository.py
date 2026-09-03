"""FIN 总账科目仓储 - GLAccountRepository。"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.fin.aggregates.gl_account_aggregate import GLAccountAggregate
from app.domain.fin.value_objects.enums import BalanceDirection, GLAccountCategory


class GLAccountRepository:
    """总账科目仓储 - upsert + 余额更新。"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, account: GLAccountAggregate) -> None:
        await self._session.execute(
            text(
                "INSERT INTO fin_gl_account "
                "(account_id, tenant_id, account_code, account_name, category, "
                "balance_direction, parent_code, opening_balance, period_debit, "
                "period_credit, closing_balance, created_at, updated_at) "
                "VALUES (:account_id, :tenant_id, :account_code, :account_name, :category, "
                ":balance_direction, :parent_code, :opening_balance, :period_debit, "
                ":period_credit, :closing_balance, :created_at, :updated_at) "
                "ON CONFLICT (tenant_id, account_code) DO UPDATE SET "
                "account_name = EXCLUDED.account_name, "
                "category = EXCLUDED.category, "
                "balance_direction = EXCLUDED.balance_direction, "
                "parent_code = EXCLUDED.parent_code, "
                "opening_balance = EXCLUDED.opening_balance, "
                "period_debit = EXCLUDED.period_debit, "
                "period_credit = EXCLUDED.period_credit, "
                "closing_balance = EXCLUDED.closing_balance, "
                "updated_at = EXCLUDED.updated_at"
            ),
            self._to_params(account),
        )

    def _to_params(self, account: GLAccountAggregate) -> dict[str, Any]:
        return {
            "account_id": str(account.account_id),
            "tenant_id": str(account.tenant_id),
            "account_code": account.account_code,
            "account_name": account.account_name,
            "category": account.category.value,
            "balance_direction": account.balance_direction.value,
            "parent_code": account.parent_code,
            "opening_balance": account.opening_balance,
            "period_debit": account.period_debit,
            "period_credit": account.period_credit,
            "closing_balance": account.closing_balance,
            "created_at": account.created_at,
            "updated_at": account.updated_at,
        }

    async def get_by_id(self, account_id: UUID) -> GLAccountAggregate | None:
        result = await self._session.execute(
            text("SELECT * FROM fin_gl_account WHERE account_id = :account_id"),
            {"account_id": str(account_id)},
        )
        row = result.first()
        return self._to_aggregate(dict(row._mapping)) if row else None

    async def get_by_code(
        self, tenant_id: UUID, account_code: str
    ) -> GLAccountAggregate | None:
        result = await self._session.execute(
            text(
                "SELECT * FROM fin_gl_account "
                "WHERE tenant_id = :tenant_id AND account_code = :account_code"
            ),
            {"tenant_id": str(tenant_id), "account_code": account_code},
        )
        row = result.first()
        return self._to_aggregate(dict(row._mapping)) if row else None

    async def list_gl_accounts(
        self,
        tenant_id: UUID,
        category: str | None = None,
        limit: int = 500,
        offset: int = 0,
    ) -> list[GLAccountAggregate]:
        conditions: list[str] = ["tenant_id = :tenant_id"]
        params: dict[str, Any] = {"tenant_id": str(tenant_id)}
        if category is not None:
            conditions.append("category = :category")
            params["category"] = category
        where_clause = " AND ".join(conditions)
        params["limit"] = limit
        params["offset"] = offset
        result = await self._session.execute(
            text(
                f"SELECT * FROM fin_gl_account WHERE {where_clause} "
                f"ORDER BY account_code ASC LIMIT :limit OFFSET :offset"
            ),
            params,
        )
        return [self._to_aggregate(dict(row._mapping)) for row in result.fetchall()]

    async def update_balance(
        self,
        account_id: UUID,
        period_debit: Decimal,
        period_credit: Decimal,
        closing_balance: Decimal,
    ) -> None:
        await self._session.execute(
            text(
                "UPDATE fin_gl_account SET period_debit = :period_debit, "
                "period_credit = :period_credit, closing_balance = :closing_balance, "
                "updated_at = now() WHERE account_id = :account_id"
            ),
            {
                "account_id": str(account_id),
                "period_debit": period_debit,
                "period_credit": period_credit,
                "closing_balance": closing_balance,
            },
        )

    def _to_aggregate(self, d: dict) -> GLAccountAggregate:
        return GLAccountAggregate(
            account_id=UUID(str(d["account_id"])),
            account_code=d["account_code"],
            account_name=d["account_name"],
            category=GLAccountCategory(d["category"]),
            balance_direction=BalanceDirection(d["balance_direction"]),
            parent_code=d.get("parent_code"),
            opening_balance=Decimal(str(d["opening_balance"])),
            period_debit=Decimal(str(d["period_debit"])),
            period_credit=Decimal(str(d["period_credit"])),
            closing_balance=Decimal(str(d["closing_balance"])),
            tenant_id=UUID(str(d["tenant_id"])),
            created_at=d.get("created_at", datetime.utcnow()),
            updated_at=d.get("updated_at", datetime.utcnow()),
        )