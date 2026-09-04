"""ApproverRoutingStrategy - 审批人路由策略模式。"""

from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from app.domain.biz_ops.enums.enums import RoutingStrategyType


class ApproverRoutingStrategy(ABC):
    """审批人路由策略抽象接口。"""

    @abstractmethod
    def route(self, config: dict, context: dict) -> list[UUID]:
        """路由审批人 - 返回审批人 ID 列表。"""
        ...


class RoleRouting(ApproverRoutingStrategy):
    """按角色路由。"""
    def route(self, config: dict, context: dict) -> list[UUID]:
        return [UUID(uid) for uid in config.get("user_ids", [])]


class DeptRouting(ApproverRoutingStrategy):
    """按部门路由。"""
    def route(self, config: dict, context: dict) -> list[UUID]:
        return [UUID(uid) for uid in config.get("user_ids", [])]


class AmountRouting(ApproverRoutingStrategy):
    """按金额阈值路由 - 超阈值升级至更高级别审批人。"""
    def route(self, config: dict, context: dict) -> list[UUID]:
        amount = float(context.get("amount", 0))
        threshold = float(config.get("threshold", 999999999))
        if amount > threshold:
            return [UUID(uid) for uid in config.get("escalate_users", [])]
        return [UUID(uid) for uid in config.get("normal_users", [])]


class SkuRouting(ApproverRoutingStrategy):
    """按 SKU 分类路由。"""
    def route(self, config: dict, context: dict) -> list[UUID]:
        sku_category = context.get("sku_category", "default")
        category_map = config.get("category_map", {})
        user_ids = category_map.get(sku_category, category_map.get("default", []))
        return [UUID(uid) for uid in user_ids]


class ScriptRouting(ApproverRoutingStrategy):
    """按自定义脚本路由。"""
    def route(self, config: dict, context: dict) -> list[UUID]:
        return [UUID(uid) for uid in config.get("user_ids", [])]


_ROUTING_STRATEGIES: dict[RoutingStrategyType, ApproverRoutingStrategy] = {
    RoutingStrategyType.ROLE: RoleRouting(),
    RoutingStrategyType.DEPT: DeptRouting(),
    RoutingStrategyType.AMOUNT: AmountRouting(),
    RoutingStrategyType.SKU: SkuRouting(),
    RoutingStrategyType.SCRIPT: ScriptRouting(),
}


def get_routing_strategy(strategy_type: RoutingStrategyType) -> ApproverRoutingStrategy:
    return _ROUTING_STRATEGIES[strategy_type]