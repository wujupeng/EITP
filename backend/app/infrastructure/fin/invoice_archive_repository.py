"""FIN 发票归档仓储 - InvoiceArchiveRepository append-only。"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class InvoiceArchiveRepository:
    """发票归档仓储 - append-only 不可修改。"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def archive(
        self,
        invoice_id: UUID,
        tenant_id: UUID,
        archive_hash: str,
        archive_payload: str,
        image_storage_id: str | None = None,
    ) -> None:
        await self._session.execute(
            text(
                "INSERT INTO fin_invoice_archive "
                "(invoice_id, tenant_id, archive_hash, archive_payload, "
                "image_storage_id, archived_at) "
                "VALUES (:invoice_id, :tenant_id, :archive_hash, :archive_payload, "
                ":image_storage_id, now()) "
                "ON CONFLICT (archive_hash) DO NOTHING"
            ),
            {
                "invoice_id": str(invoice_id),
                "tenant_id": str(tenant_id),
                "archive_hash": archive_hash,
                "archive_payload": archive_payload,
                "image_storage_id": image_storage_id,
            },
        )

    async def get_by_hash(self, archive_hash: str) -> dict[str, Any] | None:
        result = await self._session.execute(
            text("SELECT * FROM fin_invoice_archive WHERE archive_hash = :archive_hash"),
            {"archive_hash": archive_hash},
        )
        row = result.first()
        return dict(row._mapping) if row else None

    async def get_by_invoice_id(self, invoice_id: UUID) -> dict[str, Any] | None:
        result = await self._session.execute(
            text(
                "SELECT * FROM fin_invoice_archive WHERE invoice_id = :invoice_id "
                "ORDER BY archived_at DESC LIMIT 1"
            ),
            {"invoice_id": str(invoice_id)},
        )
        row = result.first()
        return dict(row._mapping) if row else None

    async def verify_integrity(self, invoice_id: UUID, expected_hash: str) -> bool:
        record = await self.get_by_invoice_id(invoice_id)
        if record is None:
            return False
        return record.get("archive_hash") == expected_hash