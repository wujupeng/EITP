"""FIN 银行流水客户端 - BankRefClient。"""

from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class BankRefClient:
    """银行流水客户端 - 导入银行对账单与解析回调。"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def import_bank_statements(
        self, tenant_id: Any, statements: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        imported: list[dict[str, Any]] = []
        for stmt in statements:
            await self._session.execute(
                text(
                    "INSERT INTO fin_bank_statement "
                    "(tenant_id, bank_ref, amount, direction, transaction_date, "
                    "counterparty_account, memo, raw_payload, imported_at) "
                    "VALUES (:tenant_id, :bank_ref, :amount, :direction, "
                    ":transaction_date, :counterparty_account, :memo, :raw_payload, now()) "
                    "ON CONFLICT (bank_ref) DO NOTHING"
                ),
                {
                    "tenant_id": str(tenant_id),
                    "bank_ref": stmt["bank_ref"],
                    "amount": stmt["amount"],
                    "direction": stmt.get("direction", "OUT"),
                    "transaction_date": stmt.get("transaction_date", date.today()),
                    "counterparty_account": stmt.get("counterparty_account"),
                    "memo": stmt.get("memo"),
                    "raw_payload": stmt.get("raw_payload", ""),
                },
            )
            imported.append(stmt)
        return imported

    async def parse_callback(self, callback_payload: dict[str, Any]) -> dict[str, Any]:
        bank_ref = callback_payload.get("bank_ref")
        status = callback_payload.get("status")
        amount = callback_payload.get("amount")
        return {
            "bank_ref": bank_ref,
            "status": status,
            "amount": amount,
            "success": status == "SUCCESS",
        }

    async def get_statement_by_ref(self, bank_ref: str) -> dict[str, Any] | None:
        result = await self._session.execute(
            text("SELECT * FROM fin_bank_statement WHERE bank_ref = :bank_ref"),
            {"bank_ref": bank_ref},
        )
        row = result.first()
        return dict(row._mapping) if row else None