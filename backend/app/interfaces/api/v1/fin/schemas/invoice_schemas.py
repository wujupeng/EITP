"""FIN 发票 Schema - 开具/匹配/校验/归档/作废请求响应模型。"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class InvoiceLineCreateRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    line_no: int | None = None
    product_id: str = Field(..., max_length=64)
    product_name: str = Field(..., max_length=256)
    quantity: Decimal = Field(..., decimal_places=2)
    tax_exclusive_amount: Decimal = Field(..., decimal_places=2)
    tax_amount: Decimal = Field(..., decimal_places=2)
    tax_inclusive_amount: Decimal = Field(..., decimal_places=2)


class InvoiceIssueRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    invoice_code: str = Field(..., max_length=32)
    invoice_no: str = Field(..., max_length=32)
    invoice_type: str = Field(..., pattern="^(GENERAL|SPECIAL|ELECTRONIC|RED)$")
    buyer_info: dict[str, str]
    seller_info: dict[str, str]
    currency: str = Field("CNY", max_length=8)
    lines: list[InvoiceLineCreateRequest] = Field(..., min_length=1)
    red_original_invoice_no: str | None = Field(None, max_length=32)
    image_storage_id: str | None = Field(None, max_length=128)


class InvoiceMatchCandidate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    business_ref_type: str
    business_ref_id: str
    amount: Decimal
    score: float | None = None


class InvoiceMatchRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    candidates: list[InvoiceMatchCandidate] = Field(..., min_length=1)


class InvoiceVerifyRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)


class InvoiceArchiveRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)


class InvoiceVoidRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    reason: str = Field(..., max_length=512)


class InvoiceLineResponse(BaseModel):
    line_no: int
    product_id: str
    product_name: str
    quantity: Decimal
    tax_exclusive_amount: Decimal
    tax_amount: Decimal
    tax_inclusive_amount: Decimal


class InvoiceResponse(BaseModel):
    invoice_id: UUID
    invoice_code: str
    invoice_no: str
    invoice_type: str
    status: str
    buyer_info: dict[str, str]
    seller_info: dict[str, str]
    currency: str
    tax_exclusive_amount: Decimal
    tax_amount: Decimal
    tax_inclusive_amount: Decimal
    business_ref_type: str | None = None
    business_ref_id: str | None = None
    archive_hash: str | None = None
    image_storage_id: str | None = None
    red_original_invoice_no: str | None = None
    lines: list[InvoiceLineResponse] = []
    created_at: datetime | None = None
    updated_at: datetime | None = None


class InvoiceListResponse(BaseModel):
    items: list[InvoiceResponse]
    total: int
    offset: int
    limit: int


class InvoiceListQuery(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    invoice_type: str | None = None
    status: str | None = None
    business_ref_type: str | None = None
    business_ref_id: str | None = None
    offset: int = Field(0, ge=0)
    limit: int = Field(50, ge=1, le=200)


class InvoiceMatchResponse(BaseModel):
    business_ref_type: str
    business_ref_id: str
    score: float