"""FIN 收款 Schema - 确认/核销/催收请求响应模型。"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ReceiptConfirmRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)


class ReceiptWriteOffLineRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    line_no: int | None = None
    ar_voucher_no: str = Field(..., max_length=64)
    write_off_amount: Decimal = Field(..., decimal_places=2)


class ReceiptWriteOffRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    write_off_lines: list[ReceiptWriteOffLineRequest] = Field(..., min_length=1)


class CollectionTaskHandleRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    handler_id: str = Field(..., max_length=64)
    content: str = Field(..., max_length=2048)
    stage: str | None = Field(None, pattern="^(INITIAL|ESCALATED|RESOLVED)$")


class ReceiptResponse(BaseModel):
    receipt_id: UUID
    receipt_no: str
    receipt_amount: Decimal
    currency: str
    status: str
    receiver_account: str
    payer_account: str
    bank_ref: str | None = None
    write_off_amount: Decimal
    arrival_time: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ReceiptListResponse(BaseModel):
    items: list[ReceiptResponse]
    total: int
    offset: int
    limit: int


class ReceiptListQuery(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    status: str | None = None
    ar_voucher_no: str | None = None
    offset: int = Field(0, ge=0)
    limit: int = Field(50, ge=1, le=200)


class CollectionTaskResponse(BaseModel):
    task_id: UUID
    ar_voucher_no: str
    stage: str
    status: str
    overdue_amount: Decimal
    overdue_days: int
    record_count: int
    created_at: datetime | None = None
    updated_at: datetime | None = None


class CollectionTaskListResponse(BaseModel):
    items: list[CollectionTaskResponse]
    total: int
    offset: int
    limit: int


class CollectionTaskListQuery(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    stage: str | None = None
    status: str | None = None
    offset: int = Field(0, ge=0)
    limit: int = Field(50, ge=1, le=200)