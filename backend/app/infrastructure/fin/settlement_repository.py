"""FIN 结算仓储 - SettlementRepository。"""

from __future__ import annotations

import json
from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.fin.aggregates.settlement_aggregate import (
    SettlementAggregate,
    SettlementLine,
)
from app.domain.fin.value_objects.enums import SettlementStatus, SettlementType
from app.domain.fin.value_objects.money import Money


class SettlementRepository:
    """结算仓储 - upsert + 多维查询。"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, settlement: SettlementAggregate) -> None:
        await self._session.execute(
            text(
                "INSERT INTO fin_settlement "
                "(settlement_id, tenant_id, settlement_no, settlement_type, status, "
                "counterparty_id, counterparty_type, settlement_lines, "
                "settlement_amount, tax_amount, currency, "
                "initiator_tenant_id, receiver_tenant_id, "
                "related_order_type, related_order_id, created_at, updated_at) "
                "VALUES (:settlement_id, :tenant_id, :settlement_no, :settlement_type, :status, "
                ":counterparty_id, :counterparty_type, :settlement_lines, "
                ":settlement_amount, :tax_amount, :currency, "
                ":initiator_tenant_id, :receiver_tenant_id, "
                ":related_order_type, :related_order_id, :created_at, :updated_at) "
                "ON CONFLICT (settlement_no) DO UPDATE SET "
                "settlement_type = EXCLUDED.settlement_type, "
                "status = EXCLUDED.status, "
                "counterparty_id = EXCLUDED.counterparty_id, "
                "counterparty_type = EXCLUDED.counterparty_type, "
                "settlement_lines = EXCLUDED.settlement_lines, "
                "settlement_amount = EXCLUDED.settlement_amount, "
                "tax_amount = EXCLUDED.tax_amount, "
                "currency = EXCLUDED.currency, "
                "initiator_tenant_id = EXCLUDED.initiator_tenant_id, "
                "receiver_tenant_id = EXCLUDED.receiver_tenant_id, "
                "related_order_type = EXCLUDED.related_order_type, "
                "related_order_id = EXCLUDED.related_order_id, "
                "updated_at = EXCLUDED.updated_at"
            ),
            self._to_params(settlement),
        )

    def _to_params(self, s: SettlementAggregate) -> dict[str, Any]:
        return {
            "settlement_id": str(s.settlement_id),
            "tenant_id": str(s.tenant_id),
            "settlement_no": s.settlement_no,
            "settlement_type": s.settlement_type.value,
            "status": s.status.value,
            "counterparty_id": s.counterparty_id,
            "counterparty_type": s.counterparty_type,
            "settlement_lines": json.dumps([self._line_to_dict(ln) for ln in s.settlement_lines]),
            "settlement_amount": s.settlement_amount.amount,
            "tax_amount": s.tax_amount.amount,
            "currency": s.currency,
            "initiator_tenant_id": str(s.initiator_tenant_id),
            "receiver_tenant_id": str(s.receiver_tenant_id) if s.receiver_tenant_id else None,
            "related_order_type": s.related_order_type,
            "related_order_id": s.related_order_id,
            "created_at": s.created_at,
            "updated_at": s.updated_at,
        }

    def _line_to_dict(self, ln: SettlementLine) -> dict[str, Any]:
        return {
            "line_no": ln.line_no,
            "product_id": ln.product_id,
            "quantity": str(ln.quantity),
            "tax_exclusive_unit_price": str(ln.tax_exclusive_unit_price.amount),
            "tax_inclusive_unit_price": str(ln.tax_inclusive_unit_price.amount),
            "tax_rate": str(ln.tax_rate),
            "currency": ln.tax_exclusive_unit_price.currency,
        }

    async def get_by_id(self, settlement_id: UUID) -> SettlementAggregate | None:
        result = await self._session.execute(
            text("SELECT * FROM fin_settlement WHERE settlement_id = :settlement_id"),
            {"settlement_id": str(settlement_id)},
        )
        row = result.first()
        return self._to_aggregate(dict(row._mapping)) if row else None

    async def get_by_no(self, settlement_no: str) -> SettlementAggregate | None:
        result = await self._session.execute(
            text("SELECT * FROM fin_settlement WHERE settlement_no = :settlement_no"),
            {"settlement_no": settlement_no},
        )
        row = result.first()
        return self._to_aggregate(dict(row._mapping)) if row else None

    async def list_settlements(
        self,
        tenant_id: UUID,
        status: str | None = None,
        settlement_type: str | None = None,
        counterparty_id: str | None = None,
        related_order_type: str | None = None,
        related_order_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[SettlementAggregate]:
        conditions: list[str] = ["tenant_id = :tenant_id"]
        params: dict[str, Any] = {"tenant_id": str(tenant_id)}
        if status is not None:
            conditions.append("status = :status")
            params["status"] = status
        if settlement_type is not None:
            conditions.append("settlement_type = :settlement_type")
            params["settlement_type"] = settlement_type
        if counterparty_id is not None:
            conditions.append("counterparty_id = :counterparty_id")
            params["counterparty_id"] = counterparty_id
        if related_order_type is not None:
            conditions.append("related_order_type = :related_order_type")
            params["related_order_type"] = related_order_type
        if related_order_id is not None:
            conditions.append("related_order_id = :related_order_id")
            params["related_order_id"] = related_order_id
        where_clause = " AND ".join(conditions)
        params["limit"] = limit
        params["offset"] = offset
        result = await self._session.execute(
            text(
                f"SELECT * FROM fin_settlement WHERE {where_clause} "
                f"ORDER BY created_at DESC LIMIT :limit OFFSET :offset"
            ),
            params,
        )
        return [self._to_aggregate(dict(row._mapping)) for row in result.fetchall()]

    async def update_status(
        self, settlement_id: UUID, status: SettlementStatus
    ) -> None:
        await self._session.execute(
            text(
                "UPDATE fin_settlement SET status = :status, updated_at = now() "
                "WHERE settlement_id = :settlement_id"
            ),
            {"settlement_id": str(settlement_id), "status": status.value},
        )

    def _to_aggregate(self, d: dict) -> SettlementAggregate:
        lines_data = json.loads(d["settlement_lines"]) if d["settlement_lines"] else []
        lines = tuple(self._line_from_dict(ln) for ln in lines_data)
        return SettlementAggregate(
            settlement_id=UUID(str(d["settlement_id"])),
            settlement_no=d["settlement_no"],
            settlement_type=SettlementType(d["settlement_type"]),
            status=SettlementStatus(d["status"]),
            counterparty_id=d["counterparty_id"],
            counterparty_type=d["counterparty_type"],
            settlement_lines=lines,
            settlement_amount=Money(Decimal(str(d["settlement_amount"]))),
            tax_amount=Money(Decimal(str(d["tax_amount"]))),
            currency=d["currency"],
            initiator_tenant_id=UUID(str(d["initiator_tenant_id"])),
            receiver_tenant_id=UUID(str(d["receiver_tenant_id"])) if d.get("receiver_tenant_id") else None,
            related_order_type=d.get("related_order_type"),
            related_order_id=d.get("related_order_id"),
            tenant_id=UUID(str(d["tenant_id"])),
            created_at=d.get("created_at", datetime.utcnow()),
            updated_at=d.get("updated_at", datetime.utcnow()),
        )

    def _line_from_dict(self, d: dict) -> SettlementLine:
        currency = d.get("currency", "CNY")
        return SettlementLine(
            line_no=d["line_no"],
            product_id=d["product_id"],
            quantity=Decimal(str(d["quantity"])),
            tax_exclusive_unit_price=Money(Decimal(str(d["tax_exclusive_unit_price"])), currency),
            tax_inclusive_unit_price=Money(Decimal(str(d["tax_inclusive_unit_price"])), currency),
            tax_rate=Decimal(str(d["tax_rate"])),
        )