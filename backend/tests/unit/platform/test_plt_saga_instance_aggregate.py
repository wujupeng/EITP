"""PLT SagaInstanceAggregate 单元测试 - 分布式事务编排与补偿。

覆盖 create() 初始 RUNNING/current_step=0、advance_step() 自增与完成态、
start_compensation()/complete_compensation() 状态流转、fail() 记录原因、
require_manual_intervention() 状态。
"""

from __future__ import annotations

import os
import sys
from uuid import uuid4

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from app.domain.platform.consistency.aggregates.saga_instance_aggregate import (
    SagaInstanceAggregate,
    SagaStatus,
)


def _make_saga(steps: list[dict] | None = None) -> SagaInstanceAggregate:
    return SagaInstanceAggregate.create(
        saga_type="tenant.provision",
        tenant_id=uuid4(),
        steps=steps or [{"name": "step-1"}, {"name": "step-2"}, {"name": "step-3"}],
        trace_id="trace-001",
    )


class SagaInstanceAggregateTest:
    """SagaInstanceAggregate 编排状态机测试。"""

    def test_create_sets_status_running_and_current_step_zero(self) -> None:
        saga = _make_saga()
        assert saga.status == SagaStatus.RUNNING
        assert saga.current_step == 0
        assert saga.compensations == []
        assert len(saga.steps) == 3

    def test_advance_step_increments_current_step(self) -> None:
        saga = _make_saga()
        advanced = saga.advance_step()
        assert advanced.current_step == 1
        assert advanced.status == SagaStatus.RUNNING
        # 原实例不变
        assert saga.current_step == 0

    def test_advance_step_completes_saga_when_all_steps_done(self) -> None:
        saga = _make_saga(steps=[{"name": "only"}])
        # 唯一步：next_step=1 >= len(steps)=1 → COMPLETED
        completed = saga.advance_step()
        assert completed.status == SagaStatus.COMPLETED
        assert completed.current_step == 1

    def test_advance_step_completes_after_all_steps(self) -> None:
        saga = _make_saga(steps=[{"name": "a"}, {"name": "b"}])
        s1 = saga.advance_step()
        assert s1.status == SagaStatus.RUNNING
        assert s1.current_step == 1
        s2 = s1.advance_step()
        assert s2.status == SagaStatus.COMPLETED
        assert s2.current_step == 2

    def test_start_compensation_sets_status_compensating(self) -> None:
        saga = _make_saga()
        compensating = saga.start_compensation()
        assert compensating.status == SagaStatus.COMPENSATING

    def test_complete_compensation_sets_status_compensated(self) -> None:
        saga = _make_saga()
        compensated = saga.complete_compensation()
        assert compensated.status == SagaStatus.COMPENSATED

    def test_fail_sets_status_failed_and_records_reason(self) -> None:
        saga = _make_saga()
        failed = saga.fail("downstream timeout")
        assert failed.status == SagaStatus.FAILED
        assert len(failed.compensations) == 1
        assert failed.compensations[0]["reason"] == "downstream timeout"
        assert "at" in failed.compensations[0]

    def test_require_manual_intervention_sets_status(self) -> None:
        saga = _make_saga()
        manual = saga.require_manual_intervention("need ops approval")
        assert manual.status == SagaStatus.MANUAL_INTERVENTION
        assert manual.compensations[0]["reason"] == "need ops approval"

    def test_updated_at_advances_on_transition(self) -> None:
        saga = _make_saga()
        advanced = saga.advance_step()
        # _with 总是刷新 updated_at
        assert advanced.updated_at >= saga.updated_at