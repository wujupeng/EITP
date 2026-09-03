"""FIN 会计核算 Schema - AR/AP/总账/凭证/报表请求响应模型。"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ARVoucherListQuery(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    status: str | None = None
    is_overdue: bool | None = None
    business_ref_type: str | None = None
    business_ref_id: str | None = None
    offset: int = Field(0, ge=0)
    limit: int = Field(100, ge=1, le=500)


class APVoucherListQuery(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    status: str | None = None
    is_overdue: bool | None = None
    business_ref_type: str | None = None
    business_ref_id: str | None = None
    offset: int = Field(0, ge=0)
    limit: int = Field(100, ge=1, le=500)


class AgingAnalysisQuery(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    as_of_date: date | None = None


class GLAccountCreateRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    account_code: str = Field(..., max_length=32)
    account_name: str = Field(..., max_length=128)
    category: str = Field(..., pattern="^(ASSET|LIABILITY|EQUITY|REVENUE|COST|EXPENSE)$")
    balance_direction: str = Field(..., pattern="^(DEBIT|CREDIT)$")
    parent_code: str | None = Field(None, max_length=32)
    opening_balance: Decimal | None = Field(None, decimal_places=2)


class GLAccountListQuery(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    category: str | None = None
    offset: int = Field(0, ge=0)
    limit: int = Field(500, ge=1, le=1000)


class GLVoucherLineCreateRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    line_no: int | None = None
    account_code: str = Field(..., max_length=32)
    debit_amount: Decimal = Field(Decimal("0"), decimal_places=2)
    credit_amount: Decimal = Field(Decimal("0"), decimal_places=2)


class GLVoucherCreateRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    voucher_no: str = Field(..., max_length=64)
    voucher_date: date
    summary: str = Field(..., max_length=256)
    period: str = Field(..., max_length=16)
    lines: list[GLVoucherLineCreateRequest] = Field(..., min_length=2)
    business_ref_type: str | None = Field(None, max_length=32)
    business_ref_id: str | None = Field(None, max_length=64)


class GLRedVoucherRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    original_voucher_no: str = Field(..., max_length=64)
    new_voucher_no: str = Field(..., max_length=64)
    period: str = Field(..., max_length=16)
    user_id: str = Field(..., max_length=64)


class PeriodCloseRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    period: str = Field(..., max_length=16)
    user_id: str = Field(..., max_length=64)


class FinancialReportQuery(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    period: str | None = None


class ARVoucherResponse(BaseModel):
    voucher_id: UUID
    voucher_no: str
    business_ref_type: str
    business_ref_id: str
    receivable_amount: Decimal
    received_amount: Decimal
    unreceived_amount: Decimal
    status: str
    credit_period_days: int
    due_date: str | None = None
    is_overdue: bool
    overdue_days: int
    aging_days: int
    aging_bucket: str


class APVoucherResponse(BaseModel):
    voucher_id: UUID
    voucher_no: str
    business_ref_type: str
    business_ref_id: str
    payable_amount: Decimal
    paid_amount: Decimal
    unpaid_amount: Decimal
    status: str
    payment_terms: int
    due_date: str | None = None
    is_overdue: bool
    overdue_days: int
    aging_days: int
    aging_bucket: str


class AgingAnalysisResponse(BaseModel):
    as_of_date: str
    ar_aging: dict[str, str]
    ar_total_unreceived: str
    ap_aging: dict[str, str]
    ap_total_unpaid: str


class GLAccountResponse(BaseModel):
    account_id: UUID
    account_code: str
    account_name: str
    category: str
    balance_direction: str
    parent_code: str | None = None
    opening_balance: Decimal
    period_debit: Decimal
    period_credit: Decimal
    closing_balance: Decimal


class GLVoucherResponse(BaseModel):
    voucher_id: UUID
    voucher_no: str
    voucher_date: date
    summary: str
    period: str
    is_period_closed: bool
    red_original_voucher_no: str | None = None
    business_ref_type: str | None = None
    business_ref_id: str | None = None
    created_at: datetime | None = None


class PeriodCloseResponse(BaseModel):
    period: str
    closed_voucher_count: int


class FinancialReportResponse(BaseModel):
    report_type: str
    data: dict[str, Any]