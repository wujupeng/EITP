"""PricingStrategyAggregate - 定价策略聚合根。"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from app.domain.biz_ops.enums.enums import PricingType, ScopeLevel
from app.domain.biz_ops.value_objects.price_config import PriceConfig
from app.domain.shared.aggregate_root import AggregateRoot
from app.domain.shared.entity import EntityId
from app.interfaces.middleware.error_handler import BizOpsError, BizOpsErrorCode


class PricingStrategyAggregate(AggregateRoot):
    """定价策略聚合根 - 采购5种+销售6种定价方法。"""

    def __init__(
        self,
        id: EntityId,
        tenant_id: UUID,
        strategy_key: str,
        strategy_name: str,
        strategy_type: PricingType,
        target_ref: str,
        price_config: PriceConfig,
        scope_level: ScopeLevel = ScopeLevel.TENANT,
        scope_ref: str | None = None,
        priority: int = 100,
        effective_from: datetime | None = None,
        effective_to: datetime | None = None,
        is_active: bool = True,
        version: int = 1,
    ) -> None:
        super().__init__(id)
        self._tenant_id = tenant_id
        self._strategy_key = strategy_key
        self._strategy_name = strategy_name
        self._strategy_type = strategy_type
        self._target_ref = target_ref
        self._price_config = price_config
        self._scope_level = scope_level
        self._scope_ref = scope_ref
        self._priority = priority
        self._effective_from = effective_from
        self._effective_to = effective_to
        self._is_active = is_active
        self._version = version
        self.validate()

    @property
    def tenant_id(self) -> UUID: return self._tenant_id
    @property
    def strategy_key(self) -> str: return self._strategy_key
    @property
    def strategy_name(self) -> str: return self._strategy_name
    @property
    def strategy_type(self) -> PricingType: return self._strategy_type
    @property
    def target_ref(self) -> str: return self._target_ref
    @property
    def price_config(self) -> PriceConfig: return self._price_config
    @property
    def scope_level(self) -> ScopeLevel: return self._scope_level
    @property
    def scope_ref(self) -> str | None: return self._scope_ref
    @property
    def priority(self) -> int: return self._priority
    @property
    def effective_from(self) -> datetime | None: return self._effective_from
    @property
    def effective_to(self) -> datetime | None: return self._effective_to
    @property
    def is_active(self) -> bool: return self._is_active
    @property
    def version(self) -> int: return self._version

    def is_effective(self, at: datetime | None = None) -> bool:
        """校验策略是否在有效期内。"""
        now = at or datetime.now(timezone.utc)
        if self._effective_from and now < self._effective_from:
            return False
        if self._effective_to and now > self._effective_to:
            return False
        return True

    def calculate_price(self, quantity: float = 1.0) -> float:
        """计算价格。"""
        return self._price_config.calculate(quantity)

    def validate(self) -> None:
        if not self._strategy_key or len(self._strategy_key) > 100:
            raise BizOpsError(BizOpsErrorCode.PRICING_CALCULATION_FAILED, "strategy_key 不能为空且不超过 100 字符")
        if self._price_config.base_price < 0:
            raise BizOpsError(BizOpsErrorCode.PRICING_CALCULATION_FAILED, "基准价不能为负")
        if not (0 <= self._price_config.discount_rate <= 1):
            raise BizOpsError(BizOpsErrorCode.PRICING_CALCULATION_FAILED, "折扣率必须在 [0, 1] 范围内")