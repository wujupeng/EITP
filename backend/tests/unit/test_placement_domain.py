"""T09 数据放置与迁移策略单元测试。"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from app.domain.placement.migration_state import (
    MigrationPhase,
    MigrationState,
    MigrationStateGuard,
)
from app.domain.placement.placement_manager import (
    PlacementManager,
    TenantScaleMetrics,
)
from app.domain.placement.placement_record import PlacementRecord, PlacementType
from app.interfaces.middleware.error_handler import DomainError, ErrorCode


class TestPlacementRecord:
    """T09-01: 放置记录。"""

    def test_create_shared_db(self) -> None:
        tenant = uuid4()
        record = PlacementRecord.create(tenant, PlacementType.SHARED_DB)
        assert record.placement == PlacementType.SHARED_DB
        assert record.connection_target == "shared-db-default"

    def test_create_dedicated_db(self) -> None:
        tenant = uuid4()
        record = PlacementRecord.create(tenant, PlacementType.DEDICATED_DB)
        assert record.placement == PlacementType.DEDICATED_DB
        assert f"{tenant}" in record.connection_target

    def test_create_dedicated_instance(self) -> None:
        tenant = uuid4()
        record = PlacementRecord.create(tenant, PlacementType.DEDICATED_INSTANCE)
        assert record.placement == PlacementType.DEDICATED_INSTANCE
        assert f"{tenant}" in record.connection_target

    def test_isolation_strength(self) -> None:
        assert PlacementType.SHARED_DB.isolation_strength == 1
        assert PlacementType.DEDICATED_DB.isolation_strength == 2
        assert PlacementType.DEDICATED_INSTANCE.isolation_strength == 3

    def test_with_placement(self) -> None:
        tenant = uuid4()
        record = PlacementRecord.create(tenant, PlacementType.SHARED_DB)
        new_record = record.with_placement(PlacementType.DEDICATED_DB)
        assert new_record.placement == PlacementType.DEDICATED_DB
        assert new_record.tenant_id == tenant


class TestPlacementManager:
    """T09-01/07: 放置管理器与大客户迁移建议。"""

    def test_set_and_get_placement(self) -> None:
        mgr = PlacementManager()
        tenant = uuid4()
        mgr.set_placement(tenant, PlacementType.DEDICATED_DB)
        record = mgr.get_placement(tenant)
        assert record is not None
        assert record.placement == PlacementType.DEDICATED_DB

    def test_get_connection_target_default(self) -> None:
        mgr = PlacementManager()
        tenant = uuid4()
        target = mgr.get_connection_target(tenant)
        assert target == "shared-db-default"

    def test_get_connection_target_cached(self) -> None:
        mgr = PlacementManager()
        tenant = uuid4()
        mgr.set_placement(tenant, PlacementType.DEDICATED_DB)
        target1 = mgr.get_connection_target(tenant)
        target2 = mgr.get_connection_target(tenant)
        assert target1 == target2

    def test_set_placement_invalidates_cache(self) -> None:
        mgr = PlacementManager()
        tenant = uuid4()
        mgr.set_placement(tenant, PlacementType.SHARED_DB)
        old_target = mgr.get_connection_target(tenant)

        mgr.set_placement(tenant, PlacementType.DEDICATED_DB)
        new_target = mgr.get_connection_target(tenant)
        assert new_target != old_target

    def test_invalidate_cache(self) -> None:
        mgr = PlacementManager()
        tenant = uuid4()
        mgr.set_placement(tenant, PlacementType.SHARED_DB)
        mgr.get_connection_target(tenant)
        mgr.invalidate_cache(tenant)

    def test_migration_suggestion_below_threshold(self) -> None:
        mgr = PlacementManager()
        metrics = TenantScaleMetrics(
            tenant_id=uuid4(),
            order_count=1000,
            warehouse_count=5,
            sku_count=500,
            user_count=50,
        )
        suggestion = mgr.evaluate_migration_suggestion(metrics)
        assert suggestion is None

    def test_migration_suggestion_exceeds_order_threshold(self) -> None:
        mgr = PlacementManager()
        metrics = TenantScaleMetrics(
            tenant_id=uuid4(),
            order_count=6_000_000,
        )
        suggestion = mgr.evaluate_migration_suggestion(metrics)
        assert suggestion is not None
        assert suggestion.suggested_placement == PlacementType.DEDICATED_DB
        assert "order_count" in suggestion.exceeded_metrics

    def test_migration_suggestion_exceeds_warehouse_threshold(self) -> None:
        mgr = PlacementManager()
        metrics = TenantScaleMetrics(
            tenant_id=uuid4(),
            warehouse_count=150,
        )
        suggestion = mgr.evaluate_migration_suggestion(metrics)
        assert suggestion is not None
        assert "warehouse_count" in suggestion.exceeded_metrics

    def test_migration_suggestion_exceeds_sku_threshold(self) -> None:
        mgr = PlacementManager()
        metrics = TenantScaleMetrics(
            tenant_id=uuid4(),
            sku_count=150_000,
        )
        suggestion = mgr.evaluate_migration_suggestion(metrics)
        assert suggestion is not None
        assert "sku_count" in suggestion.exceeded_metrics

    def test_migration_suggestion_exceeds_user_threshold(self) -> None:
        mgr = PlacementManager()
        metrics = TenantScaleMetrics(
            tenant_id=uuid4(),
            user_count=4000,
        )
        suggestion = mgr.evaluate_migration_suggestion(metrics)
        assert suggestion is not None
        assert "user_count" in suggestion.exceeded_metrics

    def test_migration_suggestion_huge_tenant_dedicated_instance(self) -> None:
        mgr = PlacementManager()
        metrics = TenantScaleMetrics(
            tenant_id=uuid4(),
            order_count=15_000_000,
        )
        suggestion = mgr.evaluate_migration_suggestion(metrics)
        assert suggestion is not None
        assert suggestion.suggested_placement == PlacementType.DEDICATED_INSTANCE


class TestMigrationState:
    """T09-03/04: 迁移状态与写入冻结。"""

    def _make_state(self) -> MigrationState:
        return MigrationState(
            task_id=uuid4(),
            tenant_id=uuid4(),
            target_placement="dedicated_db",
        )

    def test_initial_state(self) -> None:
        state = self._make_state()
        assert state.phase == MigrationPhase.PENDING
        assert state.is_write_frozen() is False

    def test_advance_to_freezing(self) -> None:
        state = self._make_state()
        state.advance_to(MigrationPhase.FREEZING)
        assert state.is_write_frozen() is True
        assert state.progress_percent == 10.0

    def test_advance_to_full_sync(self) -> None:
        state = self._make_state()
        state.advance_to(MigrationPhase.FULL_SYNC)
        assert state.is_write_frozen() is True
        assert state.progress_percent == 30.0

    def test_advance_to_completed(self) -> None:
        state = self._make_state()
        state.advance_to(MigrationPhase.COMPLETED)
        assert state.is_write_frozen() is False
        assert state.progress_percent == 100.0
        assert state.completed_at is not None

    def test_fail(self) -> None:
        state = self._make_state()
        state.fail("数据校验失败")
        assert state.phase == MigrationPhase.FAILED
        assert state.failure_reason == "数据校验失败"

    def test_rollback(self) -> None:
        state = self._make_state()
        state.advance_to(MigrationPhase.VERIFYING)
        state.rollback()
        assert state.phase == MigrationPhase.ROLLED_BACK

    def test_is_timed_out_false(self) -> None:
        state = self._make_state()
        assert state.is_timed_out() is False

    def test_is_timed_out_true(self) -> None:
        state = self._make_state()
        state.started_at = datetime.now(timezone.utc) - timedelta(minutes=31)
        assert state.is_timed_out() is True


class TestMigrationStateGuard:
    """T09-04: 迁移写入冻结守卫。"""

    def test_no_migration_allowed(self) -> None:
        MigrationStateGuard.enforce_not_frozen(uuid4(), None)

    def test_migration_frozen_rejected(self) -> None:
        state = MigrationState(
            task_id=uuid4(),
            tenant_id=uuid4(),
            target_placement="dedicated_db",
        )
        state.advance_to(MigrationPhase.FULL_SYNC)
        with pytest.raises(DomainError) as exc:
            MigrationStateGuard.enforce_not_frozen(uuid4(), state)
        assert exc.value.code == ErrorCode.MIGRATION_IN_PROGRESS

    def test_migration_completed_allowed(self) -> None:
        state = MigrationState(
            task_id=uuid4(),
            tenant_id=uuid4(),
            target_placement="dedicated_db",
        )
        state.advance_to(MigrationPhase.COMPLETED)
        MigrationStateGuard.enforce_not_frozen(uuid4(), state)

    def test_timeout_rejected(self) -> None:
        state = MigrationState(
            task_id=uuid4(),
            tenant_id=uuid4(),
            target_placement="dedicated_db",
        )
        state.started_at = datetime.now(timezone.utc) - timedelta(minutes=31)
        with pytest.raises(DomainError) as exc:
            MigrationStateGuard.enforce_not_timed_out(state)
        assert exc.value.code == ErrorCode.MIGRATION_TIMEOUT

    def test_timeout_not_triggered(self) -> None:
        state = MigrationState(
            task_id=uuid4(),
            tenant_id=uuid4(),
            target_placement="dedicated_db",
        )
        MigrationStateGuard.enforce_not_timed_out(state)


class TestMigrationPhase:
    def test_write_frozen_phases(self) -> None:
        assert MigrationPhase.FREEZING.is_write_frozen is True
        assert MigrationPhase.FULL_SYNC.is_write_frozen is True
        assert MigrationPhase.INCREMENTAL_SYNC.is_write_frozen is True
        assert MigrationPhase.VERIFYING.is_write_frozen is True
        assert MigrationPhase.SWITCHING.is_write_frozen is True

    def test_non_frozen_phases(self) -> None:
        assert MigrationPhase.PENDING.is_write_frozen is False
        assert MigrationPhase.COMPLETED.is_write_frozen is False
        assert MigrationPhase.FAILED.is_write_frozen is False
        assert MigrationPhase.ROLLED_BACK.is_write_frozen is False