"""LoginAuditRepository - 登录审计持久化。"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.audit.aggregates.login_audit_aggregate import LoginAuditEntry, LoginAction


class LoginAuditRepository:
    """登录审计仓储 - 仅追加，不可修改/删除。"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, entry: LoginAuditEntry) -> None:
        await self._session.execute(
            text(
                "INSERT INTO iam_login_audit (id, tenant_id, user_id, username, action, success, ip_address, user_agent, failure_reason, trace_id) "
                "VALUES (:id, :tid, :uid, :uname, :action, :success, :ip, :ua, :reason, :trace)"
            ),
            {
                "id": str(entry.id),
                "tid": str(entry.tenant_id) if entry.tenant_id else None,
                "uid": str(entry.user_id) if entry.user_id else None,
                "uname": entry.username,
                "action": entry.action.value,
                "success": entry.success,
                "ip": entry.ip_address,
                "ua": entry.user_agent,
                "reason": entry.failure_reason,
                "trace": entry.trace_id,
            },
        )

    async def list_by_tenant(
        self,
        tenant_id: UUID,
        offset: int = 0,
        limit: int = 50,
    ) -> list[dict]:
        result = await self._session.execute(
            text(
                "SELECT id, user_id, username, action, success, ip_address, failure_reason, created_at "
                "FROM iam_login_audit WHERE tenant_id = :tid ORDER BY created_at DESC OFFSET :off LIMIT :lim"
            ),
            {"tid": str(tenant_id), "off": offset, "lim": limit},
        )
        return [dict(zip(result.keys(), row)) for row in result.fetchall()]