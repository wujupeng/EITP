"""INV Pydantic Schema - 请求/响应模型。"""

from __future__ import annotations

from uuid import UUID
from datetime import datetime

from pydantic import BaseModel, Field


class ProductCreateRequest(BaseModel):
    product_code: str = Field(..., max_length=50)
    product_name: str = Field(..., max_length=200)
    category_id: UUID | None = None
    brand_id: UUID | None = None
    base_unit_id: UUID | None = None
    description: str | None = None


class ProductResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    product_code: str
    product_name: str
    category_id: UUID | None = None
    brand_id: UUID | None = None
    base_unit_id: UUID | None = None
    description: str | None = None
    status: str


class SkuCreateRequest(BaseModel):
    product_id: UUID
    sku_code: str = Field(..., max_length=50)
    sku_name: str = Field(..., max_length=200)
    unit_id: UUID | None = None
    specification: dict | None = None
    barcode_list: list[str] | None = None
    weight: float | None = None
    volume: float | None = None


class SkuResponse(BaseModel):
    id: UUID
    product_id: UUID
    sku_code: str
    sku_name: str
    status: str


class InventoryBalanceResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    sku_id: UUID
    warehouse_id: UUID
    on_hand: float
    reserved: float
    available: float
    in_transit: float
    inspection: float
    blocked: float
    unit_cost: float


class InventoryTransactionRequest(BaseModel):
    sku_id: UUID
    warehouse_id: UUID
    transaction_type: str
    quantity: float = Field(..., gt=0)
    idempotency_key: str = Field(..., max_length=100)
    correlation_id: str | None = None
    document_id: UUID | None = None
    document_type: str | None = None
    organization_id: UUID | None = None
    site_id: UUID | None = None
    location_id: UUID | None = None
    unit_cost: float | None = None
    reason: str | None = None


class InventoryTransactionResponse(BaseModel):
    id: UUID
    transaction_type: str
    quantity: float
    status: str
    result_ledger_id: UUID | None = None


class InventoryLedgerResponse(BaseModel):
    id: UUID
    transaction_id: UUID
    sku_id: UUID
    warehouse_id: UUID
    transaction_type: str
    direction: str
    quantity_before: float
    quantity_change: float
    quantity_after: float
    unit_cost: float | None = None
    total_cost: float | None = None
    reason: str | None = None
    operated_by: UUID
    operated_at: datetime


class DocumentCreateRequest(BaseModel):
    document_type: str
    document_number: str = Field(..., max_length=50)
    organization_id: UUID | None = None
    site_id: UUID | None = None
    warehouse_id: UUID | None = None


class DocumentResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    document_type: str
    document_number: str
    status: str
    created_by: UUID
    approved_by: UUID | None = None
    created_at: datetime


class DocumentStateTransitionRequest(BaseModel):
    action: str = Field(..., description="submit/approve/reject/execute/complete/cancel")