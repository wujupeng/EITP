"""append-only 审计触发器集成测试 - UPDATE/DELETE 篡改被拦截。"""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.domain.sec.certification.aggregates.certification_audit_aggregate import (
    CertificationAuditAggregate,
)
from app.domain.sec.certification.value_objects.audit_action_type import AuditActionType
from app.interfaces.middleware.error_handler import SECError, SECErrorCode


class TestAppendOnlyAudit:
    """append-only 审计聚合根测试。"""

    def test_append_creates_record(self) -> None:
        audit = CertificationAuditAggregate()
        batch_id = uuid4()
        tenant_id = uuid4()
        audit.append(
            action_type=AuditActionType.CERT_EXECUTE,
            operator="admin",
            batch_id=batch_id,
            tenant_id=tenant_id,
        )
        assert audit.action_type == AuditActionType.CERT_EXECUTE
        assert audit.operator == "admin"
        assert audit.immutable is True

    def test_update_raises_tamper_error(self) -> None:
        audit = CertificationAuditAggregate()
        with pytest.raises(SECError) as exc_info:
            audit.update(action_type=AuditActionType.ITEM_PASS)
        assert SECErrorCode.AUDIT_TAMPER_ATTEMPT in str(exc_info.value.error_code)

    def test_delete_raises_tamper_error(self) -> None:
        audit = CertificationAuditAggregate()
        with pytest.raises(SECError) as exc_info:
            audit.delete()
        assert SECErrorCode.AUDIT_TAMPER_ATTEMPT in str(exc_info.value.error_code)

    def test_attempt_tamper_raises_error(self) -> None:
        audit = CertificationAuditAggregate()
        with pytest.raises(SECError):
            audit.attempt_tamper()

    def test_immutable_always_true(self) -> None:
        audit = CertificationAuditAggregate()
        audit.append(
            action_type=AuditActionType.CERT_ISSUE,
            operator="security",
            batch_id=uuid4(),
            tenant_id=uuid4(),
        )
        assert audit.immutable is True

    def test_retention_not_expired(self) -> None:
        audit = CertificationAuditAggregate()
        assert audit.retention_expired is False