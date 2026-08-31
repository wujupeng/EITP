"""EITP-INV-001 成本模型与负库存策略聚合根单元测试。"""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.domain.count.aggregates.negative_stock_policy_aggregate import (
    NegativeStockPolicyAggregate,
)
from app.domain.cost.services.cost_model import (
    CostCalculationResult,
    CostModel,
    MovingAverageCostModel,
    WeightedAverageCostModel,
    get_cost_model,
)
from app.domain.inventory.value_objects.shared import NegativePolicyMode
from app.domain.shared.entity import EntityId


class MovingAverageCostModelTest:
    def test_calculate_basic_mixed_costs(self) -> None:
        model = MovingAverageCostModel()
        result = model.calculate(
            current_qty=100.0, current_unit_cost=10.0, incoming_qty=50.0, incoming_unit_cost=16.0
        )
        assert isinstance(result, CostCalculationResult)
        assert result.unit_cost == pytest.approx(12.0)
        assert result.total_cost == pytest.approx(1800.0)

    def test_calculate_with_zero_current_quantity(self) -> None:
        model = MovingAverageCostModel()
        result = model.calculate(
            current_qty=0.0, current_unit_cost=0.0, incoming_qty=100.0, incoming_unit_cost=15.0
        )
        assert result.unit_cost == pytest.approx(15.0)
        assert result.total_cost == pytest.approx(1500.0)

    def test_calculate_with_zero_total_quantity(self) -> None:
        model = MovingAverageCostModel()
        result = model.calculate(
            current_qty=0.0, current_unit_cost=10.0, incoming_qty=0.0, incoming_unit_cost=20.0
        )
        assert result.unit_cost == 0.0
        assert result.total_cost == 0.0

    def test_calculate_equal_costs_keeps_unit_cost(self) -> None:
        model = MovingAverageCostModel()
        result = model.calculate(
            current_qty=200.0, current_unit_cost=8.0, incoming_qty=300.0, incoming_unit_cost=8.0
        )
        assert result.unit_cost == pytest.approx(8.0)
        assert result.total_cost == pytest.approx(4000.0)


class WeightedAverageCostModelTest:
    def test_calculate_default_equal_weights(self) -> None:
        model = WeightedAverageCostModel()
        result = model.calculate(
            current_qty=100.0, current_unit_cost=10.0, incoming_qty=50.0, incoming_unit_cost=20.0
        )
        assert result.unit_cost == pytest.approx(15.0)
        assert result.total_cost == pytest.approx(15.0 * 150.0)

    def test_calculate_custom_weights(self) -> None:
        model = WeightedAverageCostModel(weight_current=0.7, weight_incoming=0.3)
        result = model.calculate(
            current_qty=100.0, current_unit_cost=10.0, incoming_qty=50.0, incoming_unit_cost=20.0
        )
        assert result.unit_cost == pytest.approx(13.0)
        assert result.total_cost == pytest.approx(13.0 * 150.0)

    def test_calculate_with_zero_total_quantity(self) -> None:
        model = WeightedAverageCostModel()
        result = model.calculate(
            current_qty=0.0, current_unit_cost=10.0, incoming_qty=0.0, incoming_unit_cost=20.0
        )
        assert result.unit_cost == 0.0
        assert result.total_cost == 0.0

    def test_calculate_zero_weight_sum_falls_back_to_current(self) -> None:
        model = WeightedAverageCostModel(weight_current=0.0, weight_incoming=0.0)
        result = model.calculate(
            current_qty=100.0, current_unit_cost=10.0, incoming_qty=50.0, incoming_unit_cost=20.0
        )
        assert result.unit_cost == pytest.approx(10.0)
        assert result.total_cost == pytest.approx(10.0 * 150.0)


class GetCostModelTest:
    def test_returns_moving_average_instance(self) -> None:
        model = get_cost_model("moving_average")
        assert isinstance(model, MovingAverageCostModel)
        assert isinstance(model, CostModel)

    def test_returns_weighted_average_instance(self) -> None:
        model = get_cost_model("weighted_average")
        assert isinstance(model, WeightedAverageCostModel)
        assert isinstance(model, CostModel)

    def test_invalid_model_type_raises_value_error(self) -> None:
        with pytest.raises(ValueError):
            get_cost_model("fifo")

    def test_unknown_type_raises_value_error(self) -> None:
        with pytest.raises(ValueError):
            get_cost_model("nonexistent_model")


@pytest.fixture
def tenant_id() -> uuid4:
    return uuid4()


def _make_policy(
    *,
    tenant_id: uuid4 | None = None,
    mode: NegativePolicyMode = NegativePolicyMode.GLOBAL_FORBID,
    allow_force: bool = False,
    require_approval: bool = False,
) -> NegativeStockPolicyAggregate:
    return NegativeStockPolicyAggregate(
        id=EntityId.generate(),
        tenant_id=tenant_id or uuid4(),
        mode=mode,
        allow_force=allow_force,
        require_approval=require_approval,
    )


class NegativeStockPolicyAggregateTest:
    def test_default_mode_is_global_forbid(self, tenant_id: uuid4) -> None:
        policy = NegativeStockPolicyAggregate(
            id=EntityId.generate(), tenant_id=tenant_id
        )
        assert policy.tenant_id == tenant_id
        assert policy.mode == NegativePolicyMode.GLOBAL_FORBID
        assert policy.allow_force is False
        assert policy.require_approval is False
        assert policy.approval_timeout_seconds == 3600

    @pytest.mark.parametrize(
        "mode,expected",
        [
            (NegativePolicyMode.GLOBAL_FORBID, False),
            (NegativePolicyMode.GLOBAL_ALLOW, True),
            (NegativePolicyMode.BY_BUSINESS, True),
            (NegativePolicyMode.BY_WAREHOUSE, True),
            (NegativePolicyMode.REQUIRE_APPROVAL, False),
        ],
    )
    def test_is_negative_allowed_for_each_mode(
        self, mode: NegativePolicyMode, expected: bool
    ) -> None:
        policy = _make_policy(mode=mode)
        assert policy.is_negative_allowed() is expected

    def test_can_force_negative_admin_with_allow_force(self) -> None:
        policy = _make_policy(allow_force=True)
        assert policy.can_force_negative(user_is_admin=True) is True

    def test_can_force_negative_non_admin_denied(self) -> None:
        policy = _make_policy(allow_force=True)
        assert policy.can_force_negative(user_is_admin=False) is False

    def test_can_force_negative_admin_without_allow_force(self) -> None:
        policy = _make_policy(allow_force=False)
        assert policy.can_force_negative(user_is_admin=True) is False

    def test_needs_approval_true_for_require_approval_mode(self) -> None:
        policy = _make_policy(mode=NegativePolicyMode.REQUIRE_APPROVAL)
        assert policy.needs_approval() is True

    def test_needs_approval_true_when_require_approval_flag_set(self) -> None:
        policy = _make_policy(
            mode=NegativePolicyMode.GLOBAL_ALLOW, require_approval=True
        )
        assert policy.needs_approval() is True

    def test_needs_approval_false_for_global_allow_without_flag(self) -> None:
        policy = _make_policy(mode=NegativePolicyMode.GLOBAL_ALLOW)
        assert policy.needs_approval() is False

    def test_needs_approval_false_for_global_forbid(self) -> None:
        policy = _make_policy(mode=NegativePolicyMode.GLOBAL_FORBID)
        assert policy.needs_approval() is False

    def test_approval_timeout_seconds_configurable(self) -> None:
        policy = NegativeStockPolicyAggregate(
            id=EntityId.generate(),
            tenant_id=uuid4(),
            mode=NegativePolicyMode.REQUIRE_APPROVAL,
            approval_timeout_seconds=7200,
        )
        assert policy.approval_timeout_seconds == 7200