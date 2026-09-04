"""InventoryStrategyAggregate - 库存策略聚合根。"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from app.domain.biz_ops.enums.enums import InvStrategyType, ScopeLevel
from app.domain.biz_ops.value_objects.inventory_strategy_config import InvActionConfig, InvThresholdConfig
from app.domain.shared.aggregate_root import AggregateRoot
from app.domain.shared.entity import EntityId
from app.interfaces.middleware.error_handler import BizOpsError, BizOpsErrorCode


class InventoryStrategyAggregate(AggregateRoot):
    """库存策略聚合根 - 五类策略：安全库存/预警/补货/库龄/ABC。"""

    def __init__(
        self,
        id: EntityId,
        tenant_id: UUID,
        strategy_key: str,
        strategy_name: str,
        strategy_type: InvStrategyType,
        target_ref: str,
        threshold_config: InvThresholdConfig,
        action_config: InvActionConfig,
        scope_level: ScopeLevel = ScopeLevel.TENANT,
        scope_ref: str | None = None,
        priority: int = 100,
        is_active: bool = True,
        version: int = 1,
        description: str | None = None,
    ) -> None:
        super().__init__(id)
        self._tenant_id = tenant_id
        self._strategy_key = strategy_key
        self._strategy_name = strategy_name
        self._strategy_type = strategy_type
        self._target_ref = target_ref
        self._threshold_config = threshold_config
        self._action_config = action_config
        self._scope_level = scope_level
        self._scope_ref = scope_ref
        self._priority = priority
        self._is_active = is_active
        self._version = version
        self._description = description
        self.validate()

    @property
    def tenant_id(self) -> UUID: return self._tenant_id
    @property
    def strategy_key(self) -> str: return self._strategy_key
    @property
    def strategy_name(self) -> str: return self._strategy_name
    @property
    def strategy_type(self) -> InvStrategyType: return self._strategy_type
    @property
    def target_ref(self) -> str: return self._target_ref
    @property
    def threshold_config(self) -> InvThresholdConfig: return self._threshold_config
    @property
    def action_config(self) -> InvActionConfig: return self._action_config
    @property
    def scope_level(self) -> ScopeLevel: return self._scope_level
    @property
    def scope_ref(self) -> str | None: return self._scope_ref
    @property
    def priority(self) -> int: return self._priority
    @property
    def is_active(self) -> bool: return self._is_active
    @property
    def version(self) -> int: return self._version
    @property
    def description(self) -> str | None: return self._description

    def check_safety_stock(self, current_stock: float) -> bool:
        """检查是否低于安全库存。"""
        return current_stock < self._threshold_config.safety_stock

    def check_reorder_needed(self, current_stock: float) -> bool:
        """检查是否需要补货。"""
        return current_stock <= self._threshold_config.reorder_point

    def check_aging_alert(self, stock_age_days: int) -> bool:
        """检查库龄预警。"""
        return self._threshold_config.aging_days > 0 and stock_age_days > self._threshold_config.aging_days

    def get_abc_class(self, cumulative_ratio: float) -> str:
        """获取 ABC 分类。"""
        if cumulative_ratio <= self._threshold_config.abc_a_threshold:
            return "A"
        elif cumulative_ratio <= self._threshold_config.abc_b_threshold:
            return "B"
        return "C"

    def validate(self) -> None:
        """策略分类校验、阈值合法性、动作配置完整性。"""
        if not self._strategy_key or len(self._strategy_key) > 100:
            raise BizOpsError(BizOpsErrorCode.INV_STRATEGY_CHECK_FAILED, "strategy_key 不能为空且不超过 100 字符")
        tc = self._threshold_config
        if tc.safety_stock < 0 or tc.min_stock < 0 or tc.max_stock < 0:
            raise BizOpsError(BizOpsErrorCode.INV_STRATEGY_CHECK_FAILED, "库存阈值不能为负")
        if tc.reorder_point < 0 or tc.eoq < 0:
            raise BizOpsError(BizOpsErrorCode.INV_STRATEGY_CHECK_FAILED, "补货参数不能为负")
        if self._strategy_type == InvStrategyType.REORDER and tc.reorder_point == 0 and tc.periodic_days == 0:
            raise BizOpsError(BizOpsErrorCode.INV_STRATEGY_CHECK_FAILED, "补货策略必须配置订货点或定期天数")
        if self._strategy_type == InvStrategyType.AGING and tc.aging_days <= 0:
            raise BizOpsError(BizOpsErrorCode.INV_STRATEGY_CHECK_FAILED, "库龄策略必须配置 aging_days > 0")
        if self._strategy_type == InvStrategyType.ABC:
            if not (0 < tc.abc_a_threshold < tc.abc_b_threshold <= 1):
                raise BizOpsError(BizOpsErrorCode.INV_STRATEGY_CHECK_FAILED, "ABC 阈值必须满足 0 < A < B <= 1")