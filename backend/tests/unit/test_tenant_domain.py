"""T03 租户聚合根状态机单元测试。"""

from __future__ import annotations

import pytest

from app.domain.shared.entity import EntityId
from app.domain.tenant.tenant_aggregate import TenantAggregate
from app.domain.tenant.tenant_state import DataPlacement, TenantStatus
from app.interfaces.middleware.error_handler import DomainError, ErrorCode


def _make_tenant(
    status: TenantStatus = TenantStatus.PROVISIONING,
) -> TenantAggregate:
    return TenantAggregate(
        id=EntityId.generate(),
        enterprise_name="测试企业",
        idempotency_key="TEST-KEY-001",
        status=status,
    )


class TestTenantStateMachine:
    def test_provision_success(self) -> None:
        tenant = _make_tenant(TenantStatus.PROVISIONING)
        tenant.provision()
        assert tenant.status == TenantStatus.ACTIVE
        events = list(tenant.pull_events())
        assert len(events) == 1
        assert events[0].event_type == "TenantProvisionedEvent"

    def test_provision_from_active_raises(self) -> None:
        tenant = _make_tenant(TenantStatus.ACTIVE)
        with pytest.raises(DomainError):
            tenant.provision()

    def test_disable_from_active(self) -> None:
        tenant = _make_tenant(TenantStatus.ACTIVE)
        tenant.disable()
        assert tenant.status == TenantStatus.DISABLED

    def test_disable_from_provisioning_raises(self) -> None:
        tenant = _make_tenant(TenantStatus.PROVISIONING)
        with pytest.raises(DomainError) as exc:
            tenant.disable()
        assert exc.value.code == ErrorCode.DEPROVISION_REQUIRES_DISABLE

    def test_enable_from_disabled(self) -> None:
        tenant = _make_tenant(TenantStatus.DISABLED)
        tenant.enable()
        assert tenant.status == TenantStatus.ACTIVE

    def test_deprovision_requires_confirm_token(self) -> None:
        tenant = _make_tenant(TenantStatus.DISABLED)
        with pytest.raises(DomainError) as exc:
            tenant.deprovision()
        assert exc.value.code == ErrorCode.DEPROVISION_CONFIRM_REQUIRED

    def test_deprovision_wrong_token_raises(self) -> None:
        tenant = _make_tenant(TenantStatus.DISABLED)
        with pytest.raises(DomainError) as exc:
            tenant.deprovision(confirm_token="wrong-token")
        assert exc.value.code == ErrorCode.DEPROVISION_CONFIRM_REQUIRED

    def test_deprovision_correct_token(self) -> None:
        tenant = _make_tenant(TenantStatus.DISABLED)
        tenant.deprovision(confirm_token=str(tenant.id.value))
        assert tenant.status == TenantStatus.DEPROVISIONED
        events = list(tenant.pull_events())
        assert events[-1].event_type == "TenantDeprovisionedEvent"

    def test_deprovision_from_active_raises(self) -> None:
        tenant = _make_tenant(TenantStatus.ACTIVE)
        with pytest.raises(DomainError):
            tenant.deprovision(confirm_token=str(tenant.id.value))

    def test_mark_failed_from_provisioning(self) -> None:
        tenant = _make_tenant(TenantStatus.PROVISIONING)
        tenant.mark_failed("数据库初始化失败")
        assert tenant.status == TenantStatus.FAILED

    def test_retry_provision_from_failed(self) -> None:
        tenant = _make_tenant(TenantStatus.FAILED)
        tenant.retry_provision()
        assert tenant.status == TenantStatus.PROVISIONING

    def test_migrate_to_changes_placement(self) -> None:
        tenant = _make_tenant(TenantStatus.ACTIVE)
        original_version = tenant.version
        tenant.migrate_to(DataPlacement.DEDICATED_DB)
        assert tenant.data_placement == DataPlacement.DEDICATED_DB
        assert tenant.version == original_version + 1

    def test_migrate_to_non_active_raises(self) -> None:
        tenant = _make_tenant(TenantStatus.DISABLED)
        with pytest.raises(DomainError) as exc:
            tenant.migrate_to(DataPlacement.DEDICATED_DB)
        assert exc.value.code == ErrorCode.MIGRATION_IN_PROGRESS

    def test_full_lifecycle(self) -> None:
        tenant = _make_tenant(TenantStatus.PROVISIONING)
        tenant.provision()
        assert tenant.status == TenantStatus.ACTIVE
        tenant.disable()
        assert tenant.status == TenantStatus.DISABLED
        tenant.enable()
        assert tenant.status == TenantStatus.ACTIVE
        tenant.disable()
        tenant.deprovision(confirm_token=str(tenant.id.value))
        assert tenant.status == TenantStatus.DEPROVISIONED
        events = list(tenant.pull_events())
        event_types = [e.event_type for e in events]
        assert "TenantProvisionedEvent" in event_types
        assert "TenantDisabledEvent" in event_types
        assert "TenantDeprovisionedEvent" in event_types