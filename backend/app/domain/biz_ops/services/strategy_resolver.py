"""StrategyResolver - 策略求值领域服务，包装 ConfigResolver 三层继承。"""

from __future__ import annotations

from typing import Any

from app.domain.biz_ops.enums.enums import ScopeLevel, TaxScopeLevel


class StrategyResolver:
    """策略求值器 - 三层继承（仓库级→公司级→租户级）与两层继承（公司级→租户级）。

    包装 ConfigResolver.resolve()，按策略类型构造 hierarchy_configs 列表。
    """

    @staticmethod
    def resolve_three_level(
        tenant_config: Any,
        company_config: Any | None = None,
        warehouse_config: Any | None = None,
    ) -> Any:
        """三层继承求值 - 仓库级 → 公司级 → 租户级。"""
        if warehouse_config is not None:
            return warehouse_config
        if company_config is not None:
            return company_config
        return tenant_config

    @staticmethod
    def resolve_two_level(
        tenant_config: Any,
        company_config: Any | None = None,
    ) -> Any:
        """两层继承求值 - 公司级 → 租户级。"""
        if company_config is not None:
            return company_config
        return tenant_config

    @staticmethod
    def resolve_by_priority(strategies: list[Any]) -> Any | None:
        """按优先级匹配 - 数值小的优先，相同按创建时间取最新。"""
        if not strategies:
            return None
        return sorted(strategies, key=lambda s: getattr(s, "priority", 100))[0]