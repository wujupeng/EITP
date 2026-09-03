"""FIN 发票仓储 - InvoiceRepository。"""

from __future__ import annotations

import json
from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.fin.aggregates.invoice_aggregate import (
    InvoiceAggregate,
    InvoiceLine,
)
from app.domain.fin.value_objects.enums import InvoiceStatus, InvoiceType
from app.domain.fin.value_objects.money import Money


class InvoiceRepository:
    """发票仓储 - upsert + 多维查询。"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, invoice: InvoiceAggregate) -> None:
        await self._session.execute(
            text(
                "INSERT INTO fin_invoice "
                "(invoice_id, tenant_id, invoice_code, invoice_no, invoice_type, status, "
                "buyer_info, seller_info, invoice_lines, "
                "tax_exclusive_amount, tax_amount, tax_inclusive_amount, "
                "red_original_invoice_no, archive_hash, image_storage_id, "
                "created_at, updated_at) "
                "VALUES (:invoice_id, :tenant_id, :invoice_code, :invoice_no, :invoice_type, :status, "
                ":buyer_info, :seller_info, :invoice_lines, "
                ":tax_exclusive_amount, :tax_amount, :tax_inclusive_amount, "
                ":red_original_invoice_no, :archive_hash, :image_storage_id, "
                ":created_at, :updated_at) "
                "ON CONFLICT (invoice_no) DO UPDATE SET "
                "invoice_type = EXCLUDED.invoice_type, "
                "status = EXCLUDED.status, "
                "buyer_info = EXCLUDED.buyer_info, "
                "seller_info = EXCLUDED.seller_info, "
                "invoice_lines = EXCLUDED.invoice_lines, "
                "tax_exclusive_amount = EXCLUDED.tax_exclusive_amount, "
                "tax_amount = EXCLUDED.tax_amount, "
                "tax_inclusive_amount = EXCLUDED.tax_inclusive_amount, "
                "red_original_invoice_no = EXCLUDED.red_original_invoice_no, "
                "archive_hash = EXCLUDED.archive_hash, "
                "image_storage_id = EXCLUDED.image_storage_id, "
                "updated_at = EXCLUDED.updated_at"
            ),
            self._to_params(invoice),
        )

    def _to_params(self, inv: InvoiceAggregate) -> dict[str, Any]:
        return {
            "invoice_id": str(inv.invoice_id),
            "tenant_id": str(inv.tenant_id),
            "invoice_code": inv.invoice_code,
            "invoice_no": inv.invoice_no,
            "invoice_type": inv.invoice_type.value,
            "status": inv.status.value,
            "buyer_info": json.dumps(inv.buyer_info),
            "seller_info": json.dumps(inv.seller_info),
            "invoice_lines": json.dumps([self._line_to_dict(ln) for ln in inv.invoice_lines]),
            "tax_exclusive_amount": inv.tax_exclusive_amount.amount,
            "tax_amount": inv.tax_amount.amount,
            "tax_inclusive_amount": inv.tax_inclusive_amount.amount,
            "red_original_invoice_no": inv.red_original_invoice_no,
            "archive_hash": inv.archive_hash,
            "image_storage_id": inv.image_storage_id,
            "created_at": inv.created_at,
            "updated_at": inv.updated_at,
        }

    def _line_to_dict(self, ln: InvoiceLine) -> dict[str, Any]:
        return {
            "line_no": ln.line_no,
            "product_id": ln.product_id,
            "product_name": ln.product_name,
            "quantity": str(ln.quantity),
            "tax_exclusive_amount": str(ln.tax_exclusive_amount.amount),
            "tax_amount": str(ln.tax_amount.amount),
            "tax_inclusive_amount": str(ln.tax_inclusive_amount.amount),
            "currency": ln.tax_inclusive_amount.currency,
        }

    async def get_by_id(self, invoice_id: UUID) -> InvoiceAggregate | None:
        result = await self._session.execute(
            text("SELECT * FROM fin_invoice WHERE invoice_id = :invoice_id"),
            {"invoice_id": str(invoice_id)},
        )
        row = result.first()
        return self._to_aggregate(dict(row._mapping)) if row else None

    async def get_by_no(self, invoice_no: str) -> InvoiceAggregate | None:
        result = await self._session.execute(
            text("SELECT * FROM fin_invoice WHERE invoice_no = :invoice_no"),
            {"invoice_no": invoice_no},
        )
        row = result.first()
        return self._to_aggregate(dict(row._mapping)) if row else None

    async def list_invoices(
        self,
        tenant_id: UUID,
        status: str | None = None,
        invoice_type: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[InvoiceAggregate]:
        conditions: list[str] = ["tenant_id = :tenant_id"]
        params: dict[str, Any] = {"tenant_id": str(tenant_id)}
        if status is not None:
            conditions.append("status = :status")
            params["status"] = status
        if invoice_type is not None:
            conditions.append("invoice_type = :invoice_type")
            params["invoice_type"] = invoice_type
        where_clause = " AND ".join(conditions)
        params["limit"] = limit
        params["offset"] = offset
        result = await self._session.execute(
            text(
                f"SELECT * FROM fin_invoice WHERE {where_clause} "
                f"ORDER BY created_at DESC LIMIT :limit OFFSET :offset"
            ),
            params,
        )
        return [self._to_aggregate(dict(row._mapping)) for row in result.fetchall()]

    def _to_aggregate(self, d: dict) -> InvoiceAggregate:
        lines_data = json.loads(d["invoice_lines"]) if d.get("invoice_lines") else []
        lines = tuple(self._line_from_dict(ln) for ln in lines_data)
        return InvoiceAggregate(
            invoice_id=UUID(str(d["invoice_id"])),
            invoice_code=d["invoice_code"],
            invoice_no=d["invoice_no"],
            invoice_type=InvoiceType(d["invoice_type"]),
            status=InvoiceStatus(d["status"]),
            buyer_info=json.loads(d["buyer_info"]) if d.get("buyer_info") else {},
            seller_info=json.loads(d["seller_info"]) if d.get("seller_info") else {},
            invoice_lines=lines,
            tax_exclusive_amount=Money(Decimal(str(d["tax_exclusive_amount"]))),
            tax_amount=Money(Decimal(str(d["tax_amount"]))),
            tax_inclusive_amount=Money(Decimal(str(d["tax_inclusive_amount"]))),
            red_original_invoice_no=d.get("red_original_invoice_no"),
            archive_hash=d.get("archive_hash"),
            image_storage_id=d.get("image_storage_id"),
            tenant_id=UUID(str(d["tenant_id"])),
            created_at=d.get("created_at", datetime.utcnow()),
            updated_at=d.get("updated_at", datetime.utcnow()),
        )

    def _line_from_dict(self, d: dict) -> InvoiceLine:
        currency = d.get("currency", "CNY")
        return InvoiceLine(
            line_no=d["line_no"],
            product_id=d["product_id"],
            product_name=d["product_name"],
            quantity=Decimal(str(d["quantity"])),
            tax_exclusive_amount=Money(Decimal(str(d["tax_exclusive_amount"])), currency),
            tax_amount=Money(Decimal(str(d["tax_amount"])), currency),
            tax_inclusive_amount=Money(Decimal(str(d["tax_inclusive_amount"])), currency),
        )