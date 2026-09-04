"""BIZ-OPS 操作编排 Schema - 采购/销售/库存/仓库操作请求。"""

from __future__ import annotations

from pydantic import BaseModel, Field


class OperationRequest(BaseModel):
    """通用操作请求。"""
    idempotency_key: str | None = Field(None, description="幂等键")
    entity_id: str | None = Field(None, description="实体 ID")
    entity_type: str | None = Field(None, description="实体类型")


class PurchaseOrderCreateRequest(OperationRequest):
    supplier_id: str = Field(..., description="供应商 ID")
    lines: list[dict] = Field(default_factory=list, description="订单行")


class PurchaseReceiptRequest(OperationRequest):
    order_id: str = Field(..., description="采购订单 ID")
    received_items: list[dict] = Field(default_factory=list)


class PurchaseReturnRequest(OperationRequest):
    original_receipt_id: str = Field(..., description="原收货单 ID")
    quantity: float = Field(..., gt=0, description="退货数量")
    reason: str = Field(..., description="退货原因")


class SalesOrderCreateRequest(OperationRequest):
    customer_id: str = Field(..., description="客户 ID")
    lines: list[dict] = Field(default_factory=list)
    amount: float = Field(0, ge=0, description="订单金额")
    used_amount: float = Field(0, ge=0, description="已用信用额度")
    credit_limit: float = Field(0, ge=0, description="信用额度")


class SalesShipmentRequest(OperationRequest):
    order_id: str = Field(..., description="销售订单 ID")
    items: list[dict] = Field(default_factory=list)


class SalesReturnRequest(OperationRequest):
    original_shipment_id: str = Field(..., description="原发货单 ID")
    quantity: float = Field(..., gt=0, description="退货数量")
    reason: str = Field(..., description="退货原因")


class InventoryOutboundRequest(OperationRequest):
    warehouse_id: str = Field(..., description="仓库 ID")
    sku_id: str = Field(..., description="SKU ID")
    quantity: float = Field(..., gt=0)
    available_quantity: float = Field(0, ge=0, description="可用量")
    negative_strategy: str = Field("reject", description="负库存策略")


class InventoryTransferRequest(OperationRequest):
    source_warehouse_id: str = Field(..., description="源仓库 ID")
    target_warehouse_id: str = Field(..., description="目标仓库 ID")
    sku_id: str = Field(...)
    quantity: float = Field(..., gt=0)


class InventoryCountRequest(OperationRequest):
    warehouse_id: str = Field(..., description="仓库 ID")
    status: str = Field("pending", description="状态")


class InventoryAdjustRequest(OperationRequest):
    warehouse_id: str = Field(...)
    sku_id: str = Field(...)
    adjust_quantity: float = Field(...)


class WarehouseTaskRequest(OperationRequest):
    warehouse_id: str = Field(..., description="仓库 ID")
    task_type: str = Field(..., description="作业类型")


class OperationResponse(BaseModel):
    """操作响应。"""
    operation: str
    status: str
    trace_id: str
    entity_id: str
    audit_id: str