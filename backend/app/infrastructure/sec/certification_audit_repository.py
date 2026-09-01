"""CertificationAuditRepository - append-only 审计仓储，仅支持 INSERT + 查询。"""

from __future__ import annotations

import json
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class CertificationAuditRepository:
    """append-only：仅 INSERT + 查询，不支持 UPDATE/DELETE。"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def append(self, audit: dict[str, Any]) -> UUID:
        stmt = text("""
            INSERT INTO sec_certification_audit
                (audit_id, batch_id, item_id, action_type, operator, tenant_id, before_value, after_value, evidence, immutable)
            VALUES
                (:audit_id, :batch_id, :item_id, :action_type, :operator, :tenant_id, :before_value, :after_value, :evidence, true)
        """)
        await self._session.execute(stmt, {
            "audit_id": str(audit["audit_id"]),
            "batch_id": str(audit["batch_id"]),
            "item_id": audit.get("item_id"),
            "action_type": audit["action_type"],
            "operator": audit["operator"],
            "tenant_id": str(audit["tenant_id"]),
            "before_value": json.dumps(audit["before_value"]) if audit.get("before_value") else None,
            "after_value": json.dumps(audit["after_value"]) if audit.get("after_value") else None,
            "evidence": json.dumps(audit.get("evidence", {})),
        })
        await self._session.flush()
        return audit["audit_id"]

    async def get_by_batch(self, batch_id: UUID) -> list[dict[str, Any]]:
        stmt = text("SELECT * FROM sec_certification_audit WHERE batch_id = :batch_id ORDER BY action_time")
        result = await self._session.execute(stmt, {"batch_id": str(batch_id)})
        return [dict(r) for r in result.mappings()]

    async def get_by_tenant(self, tenant_id: UUID, limit: int = 100) -> list[dict[str, Any]]:
        stmt = text("SELECT * FROM sec_certification_audit WHERE tenant_id = :tenant_id ORDER BY action_time DESC LIMIT :limit")
        result = await self._session.execute(stmt, {"tenant_id": str(tenant_id), "limit": limit})
        return [dict(r) for r in result.mappings()]