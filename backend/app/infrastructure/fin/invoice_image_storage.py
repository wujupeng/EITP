"""FIN 发票影像存储 - InvoiceImageStorage。"""

from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class InvoiceImageStorage:
    """发票影像存储 - 上传/下载/校验。"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def upload(
        self,
        tenant_id: Any,
        invoice_id: Any,
        image_data: bytes,
        content_type: str = "image/png",
    ) -> str:
        import hashlib
        from uuid import uuid4
        storage_id = str(uuid4())
        content_hash = hashlib.sha256(image_data).hexdigest()
        await self._session.execute(
            text(
                "INSERT INTO fin_invoice_image "
                "(storage_id, tenant_id, invoice_id, content_hash, content_type, "
                "image_size, image_data, uploaded_at) "
                "VALUES (:storage_id, :tenant_id, :invoice_id, :content_hash, :content_type, "
                ":image_size, :image_data, now())"
            ),
            {
                "storage_id": storage_id,
                "tenant_id": str(tenant_id),
                "invoice_id": str(invoice_id),
                "content_hash": content_hash,
                "content_type": content_type,
                "image_size": len(image_data),
                "image_data": image_data,
            },
        )
        return storage_id

    async def download(self, storage_id: str) -> dict[str, Any] | None:
        result = await self._session.execute(
            text(
                "SELECT storage_id, tenant_id, invoice_id, content_hash, "
                "content_type, image_size, image_data, uploaded_at "
                "FROM fin_invoice_image WHERE storage_id = :storage_id"
            ),
            {"storage_id": storage_id},
        )
        row = result.first()
        return dict(row._mapping) if row else None

    async def get_metadata(self, storage_id: str) -> dict[str, Any] | None:
        result = await self._session.execute(
            text(
                "SELECT storage_id, tenant_id, invoice_id, content_hash, "
                "content_type, image_size, uploaded_at "
                "FROM fin_invoice_image WHERE storage_id = :storage_id"
            ),
            {"storage_id": storage_id},
        )
        row = result.first()
        return dict(row._mapping) if row else None

    async def verify_hash(self, storage_id: str, expected_hash: str) -> bool:
        meta = await self.get_metadata(storage_id)
        if meta is None:
            return False
        return meta.get("content_hash") == expected_hash