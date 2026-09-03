"""FIN 付款 Schema - 申请/审批/执行/银行回单请求响应模型。"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class PaymentCreateRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    payment_no: str = Field(..., max_length=64)
    ap_voucher_no: str = Field(..., max_length=64)
    payment_amount: Decimal = Field(..., decimal_places=2)
    payment_method: str = Field(..., pattern="^(BANK_TRANSFER|NOTE|CASH|OTHER)$")
    payment_account: str = Field(..., max_length=64)
    payee_account: str = Field(..., max_length=64)
    currency: str = Field("CNY", max_length=8)
    expected_payment_date: date | None = None


class PaymentApproveRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    approver_id: str = Field(..., max_length=64)
    approved: bool = True
    approval_opinion: str = Field("", max_length=512)


class PaymentExecuteRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)


class PaymentBankCallbackRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    callback_payload: dict[str, Any]


class BankStatementImportRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    statements: list[dict[str, Any]] = Field(..., min_length=1)


class PaymentResponse(BaseModel):
    payment_id: UUID
    payment_no: str
    ap_voucher_no: str
    payment_amount: Decimal
    currency: str
    payment_method: str
    payment_account: str
    payee_account: str
    status: str
    approver_id: str | None = None
    approval_opinion: str | None = None
    bank_ref: str | None = None
    expected_payment_date: date | None = None
    actual_payment_date: date | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class PaymentListResponse(BaseModel):
    items: list[PaymentResponse]
    total: int
    offset: int
    limit: int


class PaymentListQuery(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    status: str | None = None
    ap_voucher_no: str | None = None
    offset: int = Field(0, ge=0)
    limit: int = Field(50, ge=1, le=200)


class BankStatementImportResponse(BaseModel):
    imported_count: int
    items: list[dict[str, Any]]