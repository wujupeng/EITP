"""主数据审计聚合根 - 承载主数据变更审计完整字段，不可变。

复用 MT-001 AuditEntry 规范，扩展主数据特有字段（version_number / reason）。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID, uuid4

from app.domain.audit.audit_entry import AuditAction


@dataclass(frozen=True)
class MasterDataAuditAggregate:
    """主数据审计聚合根 - 不可变，仅追加。

    每条记录包含：审计 ID、租户 ID、动作、实体类型、实体 ID、版本号、
    前值、新值、操作人、操作时间、变更原因、IP 地址。
    """

    audit_id: UUID
    tenant_id: UUID | None
    action: AuditAction
    entity_type: str
    entity_id: str
    version_number: int | None
    old_value: dict | None
    new_value: dict | None
    operated_by: UUID | None
    operated_at: datetime
    reason: str | None
    ip_address: str | None

    @classmethod
    def create(
        cls,
        action: AuditAction,
        entity_type: str,
        entity_id: str,
        tenant_id: UUID | None = None,
        version_number: int | None = None,
        old_value: dict | None = None,
        new_value: dict | None = None,
        operated_by: UUID | None = None,
        reason: str | None = None,
        ip_address: str | None = None,
    ) -> MasterDataAuditAggregate:
        return cls(
            audit_id=uuid4(),
            tenant_id=tenant_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            version_number=version_number,
            old_value=old_value,
            new_value=new_value,
            operated_by=operated_by,
            operated_at=datetime.now(timezone.utc),
            reason=reason,
            ip_address=ip_address,
        )

    def is_group_level(self) -> bool:
        """集团级审计记录（无 tenant_id）。"""
        return self.tenant_id is None

    def is_enterprise_level(self) -> bool:
        """企业级审计记录（有 tenant_id）。"""
        return self.tenant_id is not None