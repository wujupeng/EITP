"""FIN 对账 Schema - 创建/差异处理/报告请求响应模型。"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ReconciliationLineCreateRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    line_no: int | None = None
    business_ref_type: str = Field(..., max_length=32)
    business_ref_id: str = Field(..., max_length=64)
    system_amount: Decimal = Field(..., decimal_places=2)
    external_amount: Decimal = Field(..., decimal_places=2)
    is_matched: bool = False


class ReconciliationCreateRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    recon_no: str = Field(..., max_length=64)
    period_start: date
    period_end: date
    scope_type: str = Field(..., max_length=32)
    scope_value: str = Field(..., max_length=128)
    data_source: str = Field(..., max_length=32)
    currency: str = Field("CNY", max_length=8)
    lines: list[ReconciliationLineCreateRequest] | None = None


class ReconciliationDifferenceHandleRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    handle_action: str = Field(..., pattern="^(ACCEPT|INVESTIGATE|ADJUST|REJECT)$")
    handler_id: str = Field(..., max_length=64)
    handle_opinion: str = Field(..., max_length=512)


class ReconciliationResponse(BaseModel):
    recon_id: UUID
    recon_no: str
    period_start: date
    period_end: date
    scope_type: str
    scope_value: str
    data_source: str
    currency: str
    status: str
    system_amount: Decimal
    external_amount: Decimal
    matched_count: int
    diff_count: int
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ReconciliationListResponse(BaseModel):
    items: list[ReconciliationResponse]
    total: int
    offset: int
    limit: int


class ReconciliationListQuery(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    status: str | None = None
    scope_type: str | None = None
    scope_value: str | None = None
    offset: int = Field(0, ge=0)
    limit: int = Field(50, ge=1, le=200)


class ReconciliationDifferenceResponse(BaseModel):
    diff_id: UUID
    business_ref_type: str
    business_ref_id: str
    diff_type: str
    diff_amount: Decimal
    handle_status: str


class ReconciliationHandleRecordResponse(BaseModel):
    record_id: UUID
    diff_id: UUID
    handle_action: str
    handler_id: str
    handled_at: datetime


class ReconciliationReportResponse(BaseModel):
    recon_no: str
    period_start: str
    period_end: str
    scope_type: str
    scope_value: str
    data_source: str
    status: str
    system_amount: str
    external_amount: str
    matched_count: int
    diff_count: int
    differences: list[ReconciliationDifferenceResponse]
    handle_records: list[ReconciliationHandleRecordResponse]