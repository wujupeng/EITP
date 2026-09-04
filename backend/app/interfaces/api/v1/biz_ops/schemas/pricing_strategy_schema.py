"""BIZ-OPS 定价策略 Schema。"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class TierPriceInput(BaseModel):
    min_quantity: float = Field(..., ge=0, description="最小数量")
    max_quantity: float = Field(..., ge=0, description="最大数量")
    unit_price: float = Field(..., ge=0, description="单价")


class PriceConfigInput(BaseModel):
    base_price: float = Field(0.0, ge=0, description="基准价")
    discount_rate: float = Field(0.0, ge=0, le=1, description="折扣率")
    markup_rate: float = Field(0.0, ge=0, description="加成率")
    tier_prices: list[TierPriceInput] = Field(default_factory=list, description="阶梯价表")


class PricingStrategyCreateRequest(BaseModel):
    strategy_key: str = Field(..., max_length=100, description="策略键")
    strategy_name: str = Field(..., max_length=200, description="策略名称")
    strategy_type: str = Field(..., max_length=30, description="定价类型")
    target_ref: str = Field(..., max_length=100, description="目标引用")
    price_config: PriceConfigInput = Field(..., description="价格配置")
    scope_level: str = Field("tenant", max_length=20, description="作用域层级")
    scope_ref: str | None = Field(None, max_length=100, description="作用域引用")
    priority: int = Field(100, ge=0, le=999, description="优先级")
    effective_from: datetime | None = Field(None, description="生效开始时间")
    effective_to: datetime | None = Field(None, description="生效结束时间")
    description: str | None = Field(None, max_length=500, description="描述")


class PricingStrategyUpdateRequest(BaseModel):
    strategy_name: str | None = Field(None, max_length=200)
    price_config: PriceConfigInput | None = Field(None)
    priority: int | None = Field(None, ge=0, le=999)
    effective_from: datetime | None = Field(None)
    effective_to: datetime | None = Field(None)
    is_active: bool | None = Field(None)
    description: str | None = Field(None, max_length=500)


class PricingStrategyResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    strategy_key: str
    strategy_name: str
    strategy_type: str
    target_ref: str
    price_config: PriceConfigInput
    scope_level: str
    scope_ref: str | None = None
    priority: int
    effective_from: datetime | None = None
    effective_to: datetime | None = None
    is_active: bool
    version: int
    description: str | None = None