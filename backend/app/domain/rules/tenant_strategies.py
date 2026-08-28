"""租户级策略值对象 - 定价、税务、库存策略，各租户独立隔离。"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from uuid import UUID


class StrategyType(Enum):
    PRICING = "pricing"
    TAX = "tax"
    INVENTORY = "inventory"


@dataclass(frozen=True)
class TenantStrategy:
    """租户级策略 - 按 (tenant_id, strategy_type, strategy_key) 隔离。"""

    tenant_id: UUID
    strategy_type: StrategyType
    strategy_key: str
    value: float
    description: str = ""


@dataclass(frozen=True)
class InventoryPolicy:
    """库存策略值对象。"""

    tenant_id: UUID
    allow_negative: bool = False
    require_batch: bool = False
    require_serial: bool = False
    auto_reorder_point: float | None = None
    auto_reorder_qty: float | None = None


@dataclass(frozen=True)
class TaxPolicy:
    """税务策略值对象。"""

    tenant_id: UUID
    default_tax_rate: float = 0.13
    tax_inclusive: bool = False
    round_precision: int = 2


@dataclass(frozen=True)
class PricingPolicy:
    """定价策略值对象。"""

    tenant_id: UUID
    base_currency: str = "CNY"
    allow_manual_override: bool = True
    min_profit_margin: float | None = None
    round_precision: int = 2