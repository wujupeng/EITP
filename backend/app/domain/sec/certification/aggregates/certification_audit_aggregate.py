"""CertificationAuditAggregate 聚合根 - 认证审计，append-only，不可篡改。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from app.domain.sec.certification.value_objects.audit_action_type import AuditActionType
from app.interfaces.middleware.error_handler import SECError, SECErrorCode


@dataclass
class CertificationAuditAggregate:
    audit_id: UUID = field(default_factory=uuid4)
    batch_id: UUID = field(default_factory=uuid4)
    item_id: str | None = None
    action_type: AuditActionType = AuditActionType.CERT_EXECUTE
    action_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    operator: str = ""
    tenant_id: UUID = field(default_factory=uuid4)
    before_value: dict[str, Any] | None = None
    after_value: dict[str, Any] | None = None
    evidence: dict[str, Any] = field(default_factory=dict)
    immutable: bool = True

    def append(
        self,
        action_type: AuditActionType,
        operator: str,
        batch_id: UUID,
        tenant_id: UUID,
        item_id: str | None = None,
        before_value: dict[str, Any] | None = None,
        after_value: dict[str, Any] | None = None,
        evidence: dict[str, Any] | None = None,
    ) -> None:
        self.action_type = action_type
        self.operator = operator
        self.batch_id = batch_id
        self.tenant_id = tenant_id
        self.item_id = item_id
        self.before_value = before_value
        self.after_value = after_value
        self.evidence = evidence or {}
        self.action_time = datetime.now(timezone.utc)
        self.immutable = True

    def attempt_tamper(self) -> None:
        raise SECError(
            SECErrorCode.AUDIT_TAMPER_ATTEMPT,
            f"Audit record {self.audit_id} is immutable (append-only)",
        )

    def update(self, *args: Any, **kwargs: Any) -> None:
        self.attempt_tamper()

    def delete(self) -> None:
        self.attempt_tamper()

    @property
    def retention_expired(self) -> bool:
        return False