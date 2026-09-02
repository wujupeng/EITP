"""RollbackPlanAggregate 单元测试 - 演练状态转换 / 非演练字段不可变 / 不可变性。

覆盖 domain/rel/aggregates/rollback_plan_aggregate.py 的 create() 初始 NOT_DRILLED、
mark_drill_pass / mark_drill_fail 转换、重复演练抛 RELError、
非演练字段（plan_hash/sop/migrations/config）不可变、frozen 不可变性。
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError, is_dataclass
from uuid import UUID, uuid4

import pytest

from app.domain.rel.aggregates.rollback_plan_aggregate import RollbackPlanAggregate
from app.domain.rel.enums import DrillStatus
from app.domain.rel.error_codes import RELErrorCode
from app.domain.rel.exceptions import RELError


def _make_plan() -> RollbackPlanAggregate:
    return RollbackPlanAggregate.create(
        release_id=uuid4(),
        version_rollback_sop={"step1": "revert_tag"},
        database_rollback_migrations=[{"version": "069", "inverse": "068"}],
        config_rollback_plan={"restore": "previous"},
        plan_hash="p" * 64,
    )


class RollbackPlanAggregateTest:
    """RollbackPlanAggregate 演练状态机与字段不可变性测试。"""

    # --- create() ---

    def test_create_initial_drill_status_is_not_drilled(self) -> None:
        plan = _make_plan()
        assert plan.drill_status == DrillStatus.NOT_DRILLED
        assert plan.drill_result is None

    def test_create_generates_rollback_id(self) -> None:
        plan = _make_plan()
        assert isinstance(plan.rollback_id, UUID)

    def test_create_preserves_plan_fields(self) -> None:
        release_id = uuid4()
        plan = RollbackPlanAggregate.create(
            release_id=release_id,
            version_rollback_sop={"s": 1},
            database_rollback_migrations=[{"v": "1"}],
            config_rollback_plan={"c": 2},
            plan_hash="hash",
        )
        assert plan.release_id == release_id
        assert plan.version_rollback_sop == {"s": 1}
        assert plan.database_rollback_migrations == [{"v": "1"}]
        assert plan.config_rollback_plan == {"c": 2}
        assert plan.plan_hash == "hash"

    def test_create_generates_unique_rollback_ids(self) -> None:
        assert _make_plan().rollback_id != _make_plan().rollback_id

    # --- mark_drill_pass() ---

    def test_mark_drill_pass_transitions_to_drilled_pass(self) -> None:
        plan = _make_plan().mark_drill_pass({"duration_s": 120})
        assert plan.drill_status == DrillStatus.DRILLED_PASS
        assert plan.drill_result == {"duration_s": 120}

    def test_mark_drill_pass_from_drilled_pass_raises(self) -> None:
        plan = _make_plan().mark_drill_pass({})
        with pytest.raises(RELError) as exc:
            plan.mark_drill_pass({})
        assert exc.value.code == RELErrorCode.ROLLBACK_DRILL_FAILED

    def test_mark_drill_pass_from_drilled_fail_raises(self) -> None:
        plan = _make_plan().mark_drill_fail({})
        with pytest.raises(RELError) as exc:
            plan.mark_drill_pass({})
        assert exc.value.code == RELErrorCode.ROLLBACK_DRILL_FAILED

    # --- mark_drill_fail() ---

    def test_mark_drill_fail_transitions_to_drilled_fail(self) -> None:
        plan = _make_plan().mark_drill_fail({"error": "timeout"})
        assert plan.drill_status == DrillStatus.DRILLED_FAIL
        assert plan.drill_result == {"error": "timeout"}

    def test_mark_drill_fail_from_drilled_pass_raises(self) -> None:
        plan = _make_plan().mark_drill_pass({})
        with pytest.raises(RELError) as exc:
            plan.mark_drill_fail({})
        assert exc.value.code == RELErrorCode.ROLLBACK_DRILL_FAILED

    def test_mark_drill_fail_from_drilled_fail_raises(self) -> None:
        plan = _make_plan().mark_drill_fail({})
        with pytest.raises(RELError) as exc:
            plan.mark_drill_fail({})
        assert exc.value.code == RELErrorCode.ROLLBACK_DRILL_FAILED

    # --- 非演练字段不可变 ---

    def test_mark_drill_preserves_plan_hash(self) -> None:
        plan = _make_plan()
        drilled = plan.mark_drill_pass({})
        assert drilled.plan_hash == plan.plan_hash

    def test_mark_drill_preserves_sop_and_migrations(self) -> None:
        plan = _make_plan()
        drilled = plan.mark_drill_fail({})
        assert drilled.version_rollback_sop == plan.version_rollback_sop
        assert drilled.database_rollback_migrations == plan.database_rollback_migrations
        assert drilled.config_rollback_plan == plan.config_rollback_plan

    def test_no_methods_to_mutate_plan_fields(self) -> None:
        plan = _make_plan()
        assert not hasattr(plan, "set_plan_hash")
        assert not hasattr(plan, "update_sop")
        assert not hasattr(plan, "reset_drill")

    # --- 不可变性 ---

    def test_frozen_dataclass_is_immutable(self) -> None:
        plan = _make_plan()
        assert is_dataclass(plan)
        with pytest.raises(FrozenInstanceError):
            plan.plan_hash = "tampered"  # type: ignore[misc]
        with pytest.raises(FrozenInstanceError):
            plan.drill_status = DrillStatus.DRILLED_PASS  # type: ignore[misc]

    def test_mark_drill_returns_new_instance(self) -> None:
        plan = _make_plan()
        drilled = plan.mark_drill_pass({})
        assert plan.drill_status == DrillStatus.NOT_DRILLED
        assert drilled.drill_status == DrillStatus.DRILLED_PASS
        assert plan is not drilled