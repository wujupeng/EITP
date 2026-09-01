"""EvidenceSnapshotStore - 证据快照持久化，保留 365 天。"""

from __future__ import annotations

import json
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

_RETENTION_DAYS = 365


class EvidenceSnapshotStore:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, item_id: str, snapshot: dict[str, Any]) -> UUID:
        snapshot_id = uuid4()
        stmt = text("""
            INSERT INTO sec_evidence_snapshot
                (snapshot_id, item_id, request_log, response_log, sql_plan, rls_hits, redis_keys, audit_records)
            VALUES
                (:snapshot_id, :item_id, :request_log, :response_log, :sql_plan, :rls_hits, :redis_keys, :audit_records)
        """)
        await self._session.execute(stmt, {
            "snapshot_id": str(snapshot_id),
            "item_id": item_id,
            "request_log": json.dumps(snapshot.get("request_log", {})),
            "response_log": json.dumps(snapshot.get("response_log", {})),
            "sql_plan": snapshot.get("sql_plan", ""),
            "rls_hits": json.dumps(snapshot.get("rls_hits", [])),
            "redis_keys": json.dumps(snapshot.get("redis_keys", [])),
            "audit_records": json.dumps(snapshot.get("audit_records", [])),
        })
        await self._session.flush()
        return snapshot_id

    async def get_by_item(self, item_id: str) -> list[dict[str, Any]]:
        stmt = text("SELECT * FROM sec_evidence_snapshot WHERE item_id = :item_id ORDER BY captured_at")
        result = await self._session.execute(stmt, {"item_id": item_id})
        return [dict(r) for r in result.mappings()]

    async def purge_expired(self) -> int:
        stmt = text("DELETE FROM sec_evidence_snapshot WHERE captured_at < now() - interval ':days days'")
        result = await self._session.execute(stmt, {"days": _RETENTION_DAYS})
        return result.rowcount