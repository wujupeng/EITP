"""BIZ-OPS 库存策略 Schema。"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field


class ThresholdConfigInput(BaseModel):
    safety_stock: float = Field(0, ge=0)
    min_stock: float = Field(0, ge=0)
    max_stock: float = Field(0, ge=0)
    reorder_point: float = Field(0, ge=0)
    eoq: float = Field(0, ge=0)
    alert_threshold: float = Field(0, ge=0)
    aging_days: int = Field(0, ge=0)
    abc_a_threshold: float = Field(0.8, ge=0, le=1)
    abc_b_threshold: float = Field(0.95, ge=0, le=1)
    periodic_days: int = Field(0, ge=0)


class ActionConfigInput(BaseModel):
    action_type: str = Field("alert")
    notify_channels: list[str] = Field(default_factory=list)
    notify_recipients: list[str] = Field(default_factory=list)
    auto_create_order: bool = Field(False)
    fifo_enforce: bool = Field(False)
    expire_action: str = Field("warn")


class InventoryStrategyCreateRequest(BaseModel):
    strategy_key: str = Field(..., max_length=100)
    strategy_name: str = Field(..., max_length=200)
    strategy_type: str = Field(..., max_length=20)
    target_ref: str = Field(..., max_length=100)
    threshold_config: ThresholdConfigInput
    action_config: ActionConfigInput = Field(default_factory=ActionConfigInput)
    scope_level: str = Field("tenant", max_length=20)
    scope_ref: str | None = Field(None, max_length=100)
    priority: int = Field(100, ge=0, le=999)
    description: str | None = Field(None, max_length=500)


class InventoryStrategyUpdateRequest(BaseModel):
    strategy_name: str | None = Field(None, max_length=200)
    threshold_config: ThresholdConfigInput | None = Field(None)
    action_config: ActionConfigInput | None = Field(None)
    priority: int | None = Field(None, ge=0, le=999)
    is_active: bool | None = Field(None)
    description: str | None = Field(None, max_length=500)


class InventoryStrategyResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    strategy_key: str
    strategy_name: str
    strategy_type: str
    target_ref: str
    threshold_config: ThresholdConfigInput
    action_config: ActionConfigInput
    scope_level: str
    scope_ref: str | None = None
    priority: int
    is_active: bool
    version: int
    description: str | None = None