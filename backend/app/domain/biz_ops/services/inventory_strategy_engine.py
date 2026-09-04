"""InventoryStrategyEngine - 库存策略引擎。"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.domain.biz_ops.aggregates.inventory_strategy_aggregate import InventoryStrategyAggregate
from app.domain.biz_ops.enums.enums import ExecutionResult, InvStrategyType


@dataclass(frozen=True)
class StrategyTriggerRecord:
    """策略触发记录。"""
    strategy_id: UUID
    strategy_type: InvStrategyType
    target_ref: str
    result: ExecutionResult
    message: str
    suggestion: str = ""


class InventoryStrategyEngine:
    """库存策略引擎 - 异步策略检查、预警、补货建议、库龄检查。"""

    def check_strategies(
        self,
        strategies: list[InventoryStrategyAggregate],
        current_stock: float,
        stock_age_days: int = 0,
    ) -> list[StrategyTriggerRecord]:
        """检查库存策略 - 返回触发记录列表。"""
        records: list[StrategyTriggerRecord] = []
        for s in strategies:
            if not s.is_active:
                continue
            record = self._check_single(s, current_stock, stock_age_days)
            if record:
                records.append(record)
        return records

    def _check_single(
        self,
        strategy: InventoryStrategyAggregate,
        current_stock: float,
        stock_age_days: int,
    ) -> StrategyTriggerRecord | None:
        st = strategy.strategy_type
        if st == InvStrategyType.SAFETY_STOCK:
            if strategy.check_safety_stock(current_stock):
                return StrategyTriggerRecord(
                    strategy_id=strategy.id.value, strategy_type=st,
                    target_ref=strategy.target_ref, result=ExecutionResult.WARN,
                    message=f"库存 {current_stock} 低于安全库存 {strategy.threshold_config.safety_stock}",
                    suggestion=f"建议补货至安全库存 {strategy.threshold_config.safety_stock}",
                )
        elif st == InvStrategyType.ALERT:
            if current_stock <= strategy.threshold_config.alert_threshold:
                return StrategyTriggerRecord(
                    strategy_id=strategy.id.value, strategy_type=st,
                    target_ref=strategy.target_ref, result=ExecutionResult.WARN,
                    message=f"库存 {current_stock} 低于预警阈值 {strategy.threshold_config.alert_threshold}",
                )
        elif st == InvStrategyType.REORDER:
            if strategy.check_reorder_needed(current_stock):
                qty = strategy.threshold_config.eoq or (strategy.threshold_config.max_stock - current_stock)
                return StrategyTriggerRecord(
                    strategy_id=strategy.id.value, strategy_type=st,
                    target_ref=strategy.target_ref, result=ExecutionResult.WARN,
                    message=f"库存 {current_stock} 低于订货点 {strategy.threshold_config.reorder_point}",
                    suggestion=f"建议补货 {qty} 件（待人工确认）",
                )
        elif st == InvStrategyType.AGING:
            if strategy.check_aging_alert(stock_age_days):
                return StrategyTriggerRecord(
                    strategy_id=strategy.id.value, strategy_type=st,
                    target_ref=strategy.target_ref, result=ExecutionResult.WARN,
                    message=f"库龄 {stock_age_days} 天超过阈值 {strategy.threshold_config.aging_days} 天",
                    suggestion="FIFO 强制出库" if strategy.action_config.fifo_enforce else "",
                )
        return None