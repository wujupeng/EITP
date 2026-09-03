"""FIN 对账仓储 - ReconciliationRepository。"""

from __future__ import annotations

import json
from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.fin.aggregates.reconciliation_aggregate import (
    ReconDiffHandleRecord,
    ReconciliationAggregate,
    ReconciliationDifference,
    ReconciliationLine,
)
from app.domain.fin.value_objects.enums import (
    DifferenceType,
    HandleStatus,
    ReconciliationStatus,
)
from app.domain.fin.value_objects.money import Money


class ReconciliationRepository:
    """对账仓储 - upsert + 多维查询。"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, recon: ReconciliationAggregate) -> None:
        await self._session.execute(
            text(
                "INSERT INTO fin_reconciliation "
                "(recon_id, tenant_id, recon_no, period_start, period_end, "
                "scope_type, scope_value, data_source, status, "
                "system_amount, external_amount, matched_count, diff_count, "
                "lines, differences, handle_records, created_at, updated_at) "
                "VALUES (:recon_id, :tenant_id, :recon_no, :period_start, :period_end, "
                ":scope_type, :scope_value, :data_source, :status, "
                ":system_amount, :external_amount, :matched_count, :diff_count, "
                ":lines, :differences, :handle_records, :created_at, :updated_at) "
                "ON CONFLICT (recon_no) DO UPDATE SET "
                "period_start = EXCLUDED.period_start, "
                "period_end = EXCLUDED.period_end, "
                "scope_type = EXCLUDED.scope_type, "
                "scope_value = EXCLUDED.scope_value, "
                "data_source = EXCLUDED.data_source, "
                "status = EXCLUDED.status, "
                "system_amount = EXCLUDED.system_amount, "
                "external_amount = EXCLUDED.external_amount, "
                "matched_count = EXCLUDED.matched_count, "
                "diff_count = EXCLUDED.diff_count, "
                "lines = EXCLUDED.lines, "
                "differences = EXCLUDED.differences, "
                "handle_records = EXCLUDED.handle_records, "
                "updated_at = EXCLUDED.updated_at"
            ),
            self._to_params(recon),
        )

    def _to_params(self, r: ReconciliationAggregate) -> dict[str, Any]:
        return {
            "recon_id": str(r.recon_id),
            "tenant_id": str(r.tenant_id),
            "recon_no": r.recon_no,
            "period_start": r.period_start,
            "period_end": r.period_end,
            "scope_type": r.scope_type,
            "scope_value": r.scope_value,
            "data_source": r.data_source,
            "status": r.status.value,
            "system_amount": r.system_amount.amount,
            "external_amount": r.external_amount.amount,
            "matched_count": r.matched_count,
            "diff_count": r.diff_count,
            "lines": json.dumps([self._line_to_dict(ln) for ln in r.lines]),
            "differences": json.dumps([self._diff_to_dict(d) for d in r.differences]),
            "handle_records": json.dumps([self._record_to_dict(rec) for rec in r.handle_records]),
            "created_at": r.created_at,
            "updated_at": r.updated_at,
        }

    def _line_to_dict(self, ln: ReconciliationLine) -> dict[str, Any]:
        return {
            "line_no": ln.line_no,
            "business_ref_type": ln.business_ref_type,
            "business_ref_id": ln.business_ref_id,
            "system_amount": str(ln.system_amount.amount),
            "external_amount": str(ln.external_amount.amount),
            "is_matched": ln.is_matched,
            "currency": ln.system_amount.currency,
        }

    def _diff_to_dict(self, d: ReconciliationDifference) -> dict[str, Any]:
        return {
            "diff_id": str(d.diff_id),
            "line_no": d.line_no,
            "business_ref_type": d.business_ref_type,
            "business_ref_id": d.business_ref_id,
            "diff_type": d.diff_type.value,
            "diff_amount": str(d.diff_amount.amount),
            "handle_status": d.handle_status.value,
            "currency": d.diff_amount.currency,
        }

    def _record_to_dict(self, r: ReconDiffHandleRecord) -> dict[str, Any]:
        return {
            "record_id": str(r.record_id),
            "diff_id": str(r.diff_id),
            "handle_action": r.handle_action,
            "handler_id": r.handler_id,
            "handle_opinion": r.handle_opinion,
            "handled_at": r.handled_at.isoformat(),
        }

    async def get_by_id(self, recon_id: UUID) -> ReconciliationAggregate | None:
        result = await self._session.execute(
            text("SELECT * FROM fin_reconciliation WHERE recon_id = :recon_id"),
            {"recon_id": str(recon_id)},
        )
        row = result.first()
        return self._to_aggregate(dict(row._mapping)) if row else None

    async def get_by_no(self, recon_no: str) -> ReconciliationAggregate | None:
        result = await self._session.execute(
            text("SELECT * FROM fin_reconciliation WHERE recon_no = :recon_no"),
            {"recon_no": recon_no},
        )
        row = result.first()
        return self._to_aggregate(dict(row._mapping)) if row else None

    async def list_reconciliations(
        self,
        tenant_id: UUID,
        status: str | None = None,
        scope_type: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[ReconciliationAggregate]:
        conditions: list[str] = ["tenant_id = :tenant_id"]
        params: dict[str, Any] = {"tenant_id": str(tenant_id)}
        if status is not None:
            conditions.append("status = :status")
            params["status"] = status
        if scope_type is not None:
            conditions.append("scope_type = :scope_type")
            params["scope_type"] = scope_type
        where_clause = " AND ".join(conditions)
        params["limit"] = limit
        params["offset"] = offset
        result = await self._session.execute(
            text(
                f"SELECT * FROM fin_reconciliation WHERE {where_clause} "
                f"ORDER BY created_at DESC LIMIT :limit OFFSET :offset"
            ),
            params,
        )
        return [self._to_aggregate(dict(row._mapping)) for row in result.fetchall()]

    def _to_aggregate(self, d: dict) -> ReconciliationAggregate:
        currency = "CNY"
        lines_data = json.loads(d["lines"]) if d.get("lines") else []
        lines = tuple(self._line_from_dict(ln) for ln in lines_data)
        diffs_data = json.loads(d["differences"]) if d.get("differences") else []
        diffs = tuple(self._diff_from_dict(diff) for diff in diffs_data)
        records_data = json.loads(d["handle_records"]) if d.get("handle_records") else []
        records = tuple(self._record_from_dict(rec) for rec in records_data)
        return ReconciliationAggregate(
            recon_id=UUID(str(d["recon_id"])),
            recon_no=d["recon_no"],
            period_start=d["period_start"],
            period_end=d["period_end"],
            scope_type=d["scope_type"],
            scope_value=d["scope_value"],
            data_source=d["data_source"],
            status=ReconciliationStatus(d["status"]),
            system_amount=Money(Decimal(str(d["system_amount"])), currency),
            external_amount=Money(Decimal(str(d["external_amount"])), currency),
            matched_count=d["matched_count"],
            diff_count=d["diff_count"],
            lines=lines,
            differences=diffs,
            handle_records=records,
            tenant_id=UUID(str(d["tenant_id"])),
            created_at=d.get("created_at", datetime.utcnow()),
            updated_at=d.get("updated_at", datetime.utcnow()),
        )

    def _line_from_dict(self, d: dict) -> ReconciliationLine:
        currency = d.get("currency", "CNY")
        return ReconciliationLine(
            line_no=d["line_no"],
            business_ref_type=d["business_ref_type"],
            business_ref_id=d["business_ref_id"],
            system_amount=Money(Decimal(str(d["system_amount"])), currency),
            external_amount=Money(Decimal(str(d["external_amount"])), currency),
            is_matched=d["is_matched"],
        )

    def _diff_from_dict(self, d: dict) -> ReconciliationDifference:
        currency = d.get("currency", "CNY")
        return ReconciliationDifference(
            diff_id=UUID(str(d["diff_id"])),
            line_no=d["line_no"],
            business_ref_type=d["business_ref_type"],
            business_ref_id=d["business_ref_id"],
            diff_type=DifferenceType(d["diff_type"]),
            diff_amount=Money(Decimal(str(d["diff_amount"])), currency),
            handle_status=HandleStatus(d["handle_status"]),
        )

    def _record_from_dict(self, d: dict) -> ReconDiffHandleRecord:
        return ReconDiffHandleRecord(
            record_id=UUID(str(d["record_id"])),
            diff_id=UUID(str(d["diff_id"])),
            handle_action=d["handle_action"],
            handler_id=d["handler_id"],
            handle_opinion=d["handle_opinion"],
            handled_at=datetime.fromisoformat(d["handled_at"]),
        )