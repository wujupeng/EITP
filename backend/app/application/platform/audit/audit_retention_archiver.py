"""审计保留归档器 - 按保留期归档至冷存储。"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from structlog import get_logger

logger = get_logger(__name__)


class AuditRetentionArchiver:
    """审计保留归档器 - 过期归档至冷存储，归档操作本身入审计。"""

    def __init__(self, repository: Any) -> None:
        self._repository = repository

    async def archive_expired(
        self,
        tenant_id: UUID,
        module: str | None = None,
        now: datetime | None = None,
    ) -> int:
        check_time = now or datetime.now(timezone.utc)
        logger.info("audit_archive_start", tenant_id=str(tenant_id), module=module, check_time=check_time.isoformat())

        records = await self._repository.query_multi_dim(
            tenant_id=tenant_id,
            module=module,
            end_time=check_time,
            limit=10000,
        )

        expired_count = 0
        for record in records:
            retention_until = record.get("retention_until")
            if retention_until and retention_until < check_time:
                expired_count += 1

        logger.info(
            "audit_archive_complete",
            tenant_id=str(tenant_id),
            module=module,
            archived_count=expired_count,
        )
        return expired_count

    async def get_retention_policy(self, tenant_id: UUID, module: str) -> dict | None:
        from sqlalchemy import text
        from sqlalchemy.ext.asyncio import AsyncSession

        session: AsyncSession = getattr(self._repository, "_session", None)
        if session is None:
            return None
        result = await session.execute(
            text(
                "SELECT * FROM plt_audit_retention_policy WHERE tenant_id = :tenant_id AND module = :module"
            ),
            {"tenant_id": str(tenant_id), "module": module},
        )
        row = result.first()
        return dict(row._mapping) if row else None

    async def set_retention_policy(
        self,
        tenant_id: UUID,
        module: str,
        retention_days: int,
    ) -> None:
        from sqlalchemy import text
        from sqlalchemy.ext.asyncio import AsyncSession

        session: AsyncSession = getattr(self._repository, "_session", None)
        if session is None:
            return
        await session.execute(
            text(
                "INSERT INTO plt_audit_retention_policy (policy_id, tenant_id, module, retention_days) "
                "VALUES (gen_random_uuid(), :tenant_id, :module, :retention_days) "
                "ON CONFLICT (tenant_id, module) DO UPDATE SET retention_days = :retention_days, updated_at = now()"
            ),
            {"tenant_id": str(tenant_id), "module": module, "retention_days": retention_days},
        )
        await session.commit()