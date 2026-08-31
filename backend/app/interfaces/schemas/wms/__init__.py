"""WMS Pydantic v2 Schema - 所有 WMS 接口请求/响应模型。"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class CreateWarehouseRequest(BaseModel):
    warehouse_code: str = Field(..., max_length=64)
    warehouse_name: str = Field(..., max_length=256)
    address: str | None = None
    hierarchy_node_id: UUID | None = None


class CreateZoneRequest(BaseModel):
    warehouse_id: UUID
    zone_code: str = Field(..., max_length=64)
    zone_name: str = Field(..., max_length=256)
    zone_function: str = Field("storage", pattern="^(receiving|storage|picking|shipping|qc|blocked)$")


class CreateAreaRequest(BaseModel):
    zone_id: UUID
    area_code: str = Field(..., max_length=64)
    area_name: str = Field(..., max_length=256)


class CreateLocationRequest(BaseModel):
    warehouse_id: UUID
    zone_id: UUID
    area_id: UUID | None = None
    location_code: str = Field(..., max_length=64)
    location_type: str = Field("shelf", pattern="^(floor|shelf|cold|frozen)$")
    capacity_max_qty: float | None = None
    capacity_max_weight: float | None = None
    capacity_max_volume: float | None = None
    capacity_enforce_mode: str = Field("reject", pattern="^(warn|reject)$")
    coordinate_x: float | None = None
    coordinate_y: float | None = None
    coordinate_z: float | None = None


class CreateBinRequest(BaseModel):
    location_id: UUID
    bin_code: str = Field(..., max_length=64)


class CreateEquipmentRequest(BaseModel):
    warehouse_id: UUID
    equipment_code: str = Field(..., max_length=64)
    equipment_type: str = Field("forklift", pattern="^(forklift|pda|scanner|conveyor|agv)$")


class ToggleStatusRequest(BaseModel):
    activate: bool


class SpaceTreeResponse(BaseModel):
    warehouse_id: str
    warehouse_code: str
    warehouse_name: str
    status: str
    zones: list[dict] = []


class InventoryPositionResponse(BaseModel):
    position_id: str
    sku_id: str
    warehouse_id: str
    location_id: str
    bin_id: str | None = None
    lot_number: str | None = None
    batch_number: str | None = None
    serial_number: str | None = None
    expiry_date: str | None = None
    quantity: float
    inventory_status: str
    received_at: str | None = None
    last_updated_at: str | None = None


class CreateTaskRequest(BaseModel):
    task_type: str
    document_id: UUID
    document_type: str
    priority: str = Field("medium", pattern="^(high|medium|low)$")
    idempotency_key: str | None = None
    correlation_id: str | None = None


class AssignTaskRequest(BaseModel):
    assignee_id: UUID


class TaskResponse(BaseModel):
    task_id: str
    task_type: str
    document_id: str
    document_type: str
    assignee_id: str | None = None
    status: str
    priority: str
    inv_transaction_ids: list = []
    created_at: str | None = None
    assigned_at: str | None = None
    started_at: str | None = None
    completed_at: str | None = None


class ReceivingExecuteRequest(BaseModel):
    line_id: UUID
    received_quantity: float = Field(..., gt=0)
    location_id: UUID
    lot_number: str | None = None
    batch_number: str | None = None
    serial_numbers: list[str] = []
    idempotency_key: str | None = None


class PutawayExecuteRequest(BaseModel):
    target_location_id: UUID
    putaway_quantity: float = Field(..., gt=0)


class PickingExecuteRequest(BaseModel):
    line_id: UUID
    picked_quantity: float = Field(..., gt=0)


class TransferExecuteRequest(BaseModel):
    line_id: UUID
    transfer_quantity: float = Field(..., gt=0)


class TransferApproveRequest(BaseModel):
    opinion: str = ""


class ShippingExecuteRequest(BaseModel):
    logistics_no: str
    logistics_company: str


class ReconcileDiffResponse(BaseModel):
    diff_id: str
    sku_id: str
    warehouse_id: str
    wms_quantity: float
    inv_quantity: float
    diff_quantity: float
    diff_type: str
    status: str
    created_at: str | None = None


class ReconcileResolveRequest(BaseModel):
    resolution_note: str