"""RedisKeyViolationRecorder - 违规键记录器。"""

from __future__ import annotations

import json
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.sec.redis_key_scanner import KeyViolation


class RedisKeyViolationRecorder:
    """持久化违规键到 sec_redis_key_violation 表 + 触发告警。"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def record_violations(
        self,
        violations: list[KeyViolation],
        batch_id: UUID | None = None,
        tenant_id: UUID | None = None,
    ) -> list[UUID]:
        ids: list[UUID] = []
        for v in violations:
            violation_id = uuid4()
            stmt = text("""
                INSERT INTO sec_redis_key_violation
                    (violation_id, batch_id, violation_key, violation_type, expected_prefix, actual_prefix, handling_status, tenant_id)
                VALUES
                    (:violation_id, :batch_id, :violation_key, :violation_type, :expected_prefix, :actual_prefix, 'pending', :tenant_id)
            """)
            await self._session.execute(stmt, {
                "violation_id": str(violation_id),
                "batch_id": str(batch_id) if batch_id else None,
                "violation_key": v.key,
                "violation_type": v.violation_type,
                "expected_prefix": v.expected_prefix,
                "actual_prefix": v.actual_prefix,
                "tenant_id": str(tenant_id) if tenant_id else None,
            })
            ids.append(violation_id)
        await self._session.flush()
        return ids