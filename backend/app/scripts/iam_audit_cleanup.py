"""T16-03: IAM 审计数据清理任务。

定期清理：
1. iam_token_revocation 表中过期条目（expires_at < now()）
2. iam_login_audit 表超期归档（保留期 ≥180 天）

用法：python -m scripts.iam_audit_cleanup
或通过 cron: 0 3 * * * cd /home/debian/EITP/backend && .venv/bin/python -m scripts.iam_audit_cleanup
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.session import get_db_session

logger = logging.getLogger(__name__)

TOKEN_REVOCATION_RETENTION_HOURS = 24
LOGIN_AUDIT_RETENTION_DAYS = 180


async def cleanup_expired_revocations(session: AsyncSession) -> int:
    result = await session.execute(
        text(
            "DELETE FROM iam_token_revocation "
            "WHERE expires_at IS NOT NULL AND expires_at < now()"
        )
    )
    await session.commit()
    deleted = result.rowcount or 0
    logger.info("cleanup_revocations", deleted=deleted)
    return deleted


async def archive_old_login_audits(session: AsyncSession, retention_days: int = LOGIN_AUDIT_RETENTION_DAYS) -> int:
    cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
    result = await session.execute(
        text(
            "DELETE FROM iam_login_audit WHERE created_at < :cutoff"
        ),
        {"cutoff": cutoff},
    )
    await session.commit()
    archived = result.rowcount or 0
    logger.info("archive_login_audits", archived=archived, cutoff=cutoff.isoformat())
    return archived


async def run_cleanup() -> None:
    logger.info("iam_audit_cleanup_start")
    async for session in get_db_session():
        rev_deleted = await cleanup_expired_revocations(session)
        audit_archived = await archive_old_login_audits(session)
        logger.info(
            "iam_audit_cleanup_done",
            revocations_deleted=rev_deleted,
            audits_archived=audit_archived,
        )
        break


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    asyncio.run(run_cleanup())