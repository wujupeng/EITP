"""FIN 结算 Schema - 创建/确认/取消/查询请求响应模型。"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class SettlementLineCreateRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    line_no: int | None = None
    product_id: str = Field(..., max_length=64)
    quantity: Decimal = Field(..., decimal_places=2)
    tax_exclusive_unit_price: Decimal = Field(..., decimal_places=2)
    tax_inclusive_unit_price: Decimal = Field(..., decimal_places=2)
    tax_rate: Decimal = Field(..., decimal_places=4)


class SettlementCreateRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    settlement_no: str = Field(..., max_length=64)
    settlement_type: str = Field(..., pattern="^(PURCHASE|SALES|CROSS_TENANT)$")
    counterparty_id: str = Field(..., max_length=64)
    counterparty_type: str = Field("SUPPLIER", max_length=32)
    related_order_type: str | None = Field(None, max_length=32)
    related_order_id: str | None = Field(None, max_length=64)
    currency: str = Field("CNY", max_length=8)
    receiver_tenant_id: UUID | None = None
    lines: list[SettlementLineCreateRequest] = Field(..., min_length=1)


class SettlementConfirmRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)


class SettlementCrossTenantConfirmRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    initiator_tenant_id: UUID
    receiver_tenant_id: UUID


class SettlementCancelRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    reason: str = Field("", max_length=512)


class SettlementLineResponse(BaseModel):
    line_no: int
    product_id: str
    quantity: Decimal
    tax_exclusive_unit_price: Decimal
    tax_inclusive_unit_price: Decimal
    tax_rate: Decimal
    line_amount: Decimal
    line_tax_amount: Decimal


class SettlementResponse(BaseModel):
    settlement_id: UUID
    settlement_no: str
    settlement_type: str
    status: str
    counterparty_id: str
    counterparty_type: str
    currency: str
    settlement_amount: Decimal
    tax_amount: Decimal
    related_order_type: str | None = None
    related_order_id: str | None = None
    initiator_tenant_id: UUID | None = None
    receiver_tenant_id: UUID | None = None
    lines: list[SettlementLineResponse] = []
    created_at: datetime | None = None
    updated_at: datetime | None = None


class SettlementListResponse(BaseModel):
    items: list[SettlementResponse]
    total: int
    offset: int
    limit: int


class SettlementListQuery(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    settlement_type: str | None = None
    status: str | None = None
    counterparty_id: str | None = None
    offset: int = Field(0, ge=0)
    limit: int = Field(50, ge=1, le=200)