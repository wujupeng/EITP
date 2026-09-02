"""PLT TenantLifecycleAggregate / TenantQuotaAggregate 单元测试 - 租户状态机与配额。

覆盖 create() 初始 ACTIVE、freeze()/unfreeze()/archive() 合法流转、非法流转抛 PLTError、
is_active/is_frozen/is_archived 辅助方法；TenantQuotaAggregate.create() 默认配额、
check_quota() 限内/超限、record_usage() 自增。
"""

from __future__ import annotations

import os
import sys
from uuid import uuid4

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from app.domain.platform.exceptions import PLTError
from app.domain.platform.tenant.aggregates.tenant_lifecycle_aggregate import (
    TenantLifecycleAggregate,
    TenantLifecycleState,
    TenantQuotaAggregate,
)


class TenantLifecycleAggregateTest:
    """TenantLifecycleAggregate 状态机测试。"""

    def test_create_sets_state_to_active(self) -> None:
        tenant_id = uuid4()
        lifecycle = TenantLifecycleAggregate.create(tenant_id)
        assert lifecycle.state == TenantLifecycleState.ACTIVE
        assert lifecycle.reason is None
        assert lifecycle.tenant_id == tenant_id

    def test_freeze_transitions_active_to_frozen(self) -> None:
        lifecycle = TenantLifecycleAggregate.create(uuid4())
        frozen = lifecycle.freeze("unpaid")
        assert frozen.state == TenantLifecycleState.FROZEN
        assert frozen.reason == "unpaid"

    def test_unfreeze_transitions_frozen_to_active(self) -> None:
        lifecycle = TenantLifecycleAggregate.create(uuid4()).freeze("unpaid")
        active = lifecycle.unfreeze("paid")
        assert active.state == TenantLifecycleState.ACTIVE
        assert active.reason == "paid"

    def test_archive_transitions_deprovisioning_to_archived(self) -> None:
        # ACTIVE -> DEPROVISIONING -> ARCHIVED
        lifecycle = TenantLifecycleAggregate.create(uuid4()).start_deprovision("offboard")
        assert lifecycle.state == TenantLifecycleState.DEPROVISIONING
        archived = lifecycle.archive("retention done")
        assert archived.state == TenantLifecycleState.ARCHIVED

    def test_invalid_transition_raises_plt_error(self) -> None:
        # ACTIVE 不能直接 ARCHIVED
        lifecycle = TenantLifecycleAggregate.create(uuid4())
        with pytest.raises(PLTError) as exc:
            lifecycle.archive("skip deprovision")
        assert exc.value.code.name == "TENANT_INVALID_TRANSITION"
        assert "非法状态转换" in exc.value.message

    def test_invalid_transition_from_archived_raises(self) -> None:
        # ARCHIVED 是终态，无任何合法转换
        archived = TenantLifecycleAggregate.create(uuid4()).start_deprovision("x").archive("done")
        with pytest.raises(PLTError):
            archived.unfreeze("try revive")

    def test_complete_deprovision_from_deprovisioning_raises(self) -> None:
        # 状态机中 DEPROVISIONING 仅允许 -> {ARCHIVED, ACTIVE}，无 DEPROVISIONED；
        # complete_deprovision 在该状态下应抛 PLTError（覆盖 _transition 调用行）
        deprovisioning = TenantLifecycleAggregate.create(uuid4()).start_deprovision("offboard")
        with pytest.raises(PLTError) as exc:
            deprovisioning.complete_deprovision("done")
        assert exc.value.code.name == "TENANT_INVALID_TRANSITION"

    def test_is_active_is_frozen_is_archived_helpers(self) -> None:
        lifecycle = TenantLifecycleAggregate.create(uuid4())
        assert lifecycle.is_active() is True
        assert lifecycle.is_frozen() is False
        assert lifecycle.is_archived() is False

        frozen = lifecycle.freeze("x")
        assert frozen.is_frozen() is True
        assert frozen.is_active() is False

        archived = lifecycle.start_deprovision("x").archive("done")
        assert archived.is_archived() is True
        assert archived.is_active() is False


class TenantQuotaAggregateTest:
    """TenantQuotaAggregate 配额检查测试。"""

    def test_create_with_defaults(self) -> None:
        quota = TenantQuotaAggregate.create(uuid4())
        assert quota.max_users == 100
        assert quota.max_orders_per_day == 10000
        assert quota.max_storage_mb == 10240
        assert quota.max_api_calls_per_minute == 1000
        assert quota.max_concurrent_requests == 100
        assert quota.current_usage == {}

    def test_create_with_custom_limits(self) -> None:
        quota = TenantQuotaAggregate.create(uuid4(), max_users=50, max_orders_per_day=500)
        assert quota.max_users == 50
        assert quota.max_orders_per_day == 500

    def test_check_quota_returns_true_when_within_limits(self) -> None:
        quota = TenantQuotaAggregate.create(uuid4(), max_users=100)
        assert quota.check_quota("users", 50) is True
        assert quota.check_quota("users", 100) is True  # 恰好等于上限

    def test_check_quota_returns_false_when_exceeding_limits(self) -> None:
        quota = TenantQuotaAggregate.create(uuid4(), max_users=100)
        assert quota.check_quota("users", 101) is False

    def test_check_quota_accounts_for_current_usage(self) -> None:
        quota = TenantQuotaAggregate.create(uuid4(), max_users=100)
        used = quota.record_usage("users", 80)
        # 已用 80，再申请 30 → 110 > 100
        assert used.check_quota("users", 30) is False
        # 再申请 20 → 100 <= 100
        assert used.check_quota("users", 20) is True

    def test_check_quota_unknown_resource_returns_true(self) -> None:
        # 未知 resource 无 max_{resource} 属性，默认放行
        quota = TenantQuotaAggregate.create(uuid4())
        assert quota.check_quota("unknown_resource", 99999) is True

    def test_record_usage_increments_usage(self) -> None:
        quota = TenantQuotaAggregate.create(uuid4(), max_users=100)
        q1 = quota.record_usage("users", 30)
        assert q1.current_usage["users"] == 30
        q2 = q1.record_usage("users", 20)
        assert q2.current_usage["users"] == 50
        # 原实例不可变
        assert quota.current_usage == {}
        assert q1.current_usage["users"] == 30