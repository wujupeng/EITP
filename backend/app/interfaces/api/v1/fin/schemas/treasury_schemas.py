"""FIN 资金中心 Schema - 账户/调拨/冻结/预测请求响应模型。"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class TreasuryAccountCreateRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    account_no: str = Field(..., max_length=64)
    account_type: str = Field(..., pattern="^(BANK|ALIPAY|WECHAT|PETTY|OTHER)$")
    currency: str = Field("CNY", max_length=8)
    opening_balance: Decimal = Field(Decimal("0"), decimal_places=2)


class TreasuryAccountListQuery(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    account_type: str | None = None
    currency: str | None = None
    offset: int = Field(0, ge=0)
    limit: int = Field(100, ge=1, le=500)


class TreasuryTransferCreateRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    transfer_no: str = Field(..., max_length=64)
    from_account_id: UUID
    to_account_id: UUID
    transfer_amount: Decimal = Field(..., decimal_places=2)
    reason: str = Field(..., max_length=512)
    currency: str = Field("CNY", max_length=8)


class TreasuryTransferApproveRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    approver_id: str = Field(..., max_length=64)


class TreasuryAccountFreezeRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    amount: Decimal = Field(..., decimal_places=2)
    currency: str = Field("CNY", max_length=8)


class TreasuryForecastQuery(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    forecast_days: int = Field(30, ge=1, le=365)


class TreasuryAccountResponse(BaseModel):
    account_id: UUID
    account_no: str
    account_type: str
    currency: str
    balance: Decimal
    frozen_amount: Decimal
    available_balance: Decimal


class TreasuryAccountBalanceResponse(BaseModel):
    account_no: str
    currency: str
    balance: Decimal
    frozen_amount: Decimal
    available_balance: Decimal


class TreasuryTransferResponse(BaseModel):
    transfer_id: UUID
    transfer_no: str
    from_account_id: UUID
    to_account_id: UUID
    transfer_amount: Decimal
    currency: str
    reason: str
    status: str
    approver_ids: list[str] = []
    created_at: datetime | None = None
    updated_at: datetime | None = None


class TreasuryForecastResponse(BaseModel):
    forecast_date: str
    forecast_days: int
    total_balance: str
    total_frozen: str
    total_available: str
    pending_outflow: str
    projected_available: str
    account_count: int