"""成本模型抽象接口 + 移动平均/加权平均 V1 实现。"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class CostCalculationResult:
    unit_cost: float
    total_cost: float


class CostModel(ABC):
    """成本模型抽象接口。"""

    @abstractmethod
    def calculate(
        self,
        current_qty: float,
        current_unit_cost: float,
        incoming_qty: float,
        incoming_unit_cost: float,
    ) -> CostCalculationResult:
        ...


class MovingAverageCostModel(CostModel):
    """移动平均成本模型。"""

    def calculate(
        self,
        current_qty: float,
        current_unit_cost: float,
        incoming_qty: float,
        incoming_unit_cost: float,
    ) -> CostCalculationResult:
        total_qty = current_qty + incoming_qty
        if total_qty <= 0:
            return CostCalculationResult(unit_cost=0.0, total_cost=0.0)
        total_value = current_qty * current_unit_cost + incoming_qty * incoming_unit_cost
        new_unit_cost = total_value / total_qty
        return CostCalculationResult(unit_cost=new_unit_cost, total_cost=total_value)


class WeightedAverageCostModel(CostModel):
    """加权平均成本模型。"""

    def __init__(self, weight_current: float = 0.5, weight_incoming: float = 0.5) -> None:
        self._weight_current = weight_current
        self._weight_incoming = weight_incoming

    def calculate(
        self,
        current_qty: float,
        current_unit_cost: float,
        incoming_qty: float,
        incoming_unit_cost: float,
    ) -> CostCalculationResult:
        total_qty = current_qty + incoming_qty
        if total_qty <= 0:
            return CostCalculationResult(unit_cost=0.0, total_cost=0.0)
        w_sum = self._weight_current + self._weight_incoming
        if w_sum <= 0:
            return CostCalculationResult(
                unit_cost=current_unit_cost,
                total_cost=current_unit_cost * total_qty,
            )
        new_unit_cost = (
            self._weight_current * current_unit_cost
            + self._weight_incoming * incoming_unit_cost
        ) / w_sum
        return CostCalculationResult(
            unit_cost=new_unit_cost,
            total_cost=new_unit_cost * total_qty,
        )


def get_cost_model(model_type: str) -> CostModel:
    if model_type == "moving_average":
        return MovingAverageCostModel()
    if model_type == "weighted_average":
        return WeightedAverageCostModel()
    raise ValueError(f"不支持的成本模型: {model_type}")
