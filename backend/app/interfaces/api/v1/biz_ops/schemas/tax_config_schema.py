"""BIZ-OPS 税务配置 Schema。"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field


class TaxRateEntryInput(BaseModel):
    tax_type: str = Field(..., description="税种: vat/consumption/customs/surtax")
    rate: float = Field(..., ge=0, le=1, description="税率 [0, 1]")
    is_default: bool = Field(False, description="是否默认税率")


class SpecialTaxRuleInput(BaseModel):
    rule: str = Field(..., description="规则: exempt/zero_rate/not_taxable")
    description: str = Field("", description="描述")


class TaxConfigCreateRequest(BaseModel):
    config_key: str = Field(..., max_length=100)
    config_name: str = Field(..., max_length=200)
    tax_rates: list[TaxRateEntryInput] = Field(..., min_length=1)
    tax_flag: str = Field("tax_exclusive", description="含税标志")
    direction: str = Field("output", description="方向: input/output")
    scope_level: str = Field("tenant", max_length=20)
    scope_ref: str | None = Field(None, max_length=100)
    special_rules: list[SpecialTaxRuleInput] = Field(default_factory=list)
    description: str | None = Field(None, max_length=500)


class TaxConfigUpdateRequest(BaseModel):
    config_name: str | None = Field(None, max_length=200)
    tax_rates: list[TaxRateEntryInput] | None = Field(None)
    tax_flag: str | None = Field(None)
    direction: str | None = Field(None)
    is_active: bool | None = Field(None)
    description: str | None = Field(None, max_length=500)


class TaxConfigResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    config_key: str
    config_name: str
    tax_rates: list[TaxRateEntryInput]
    tax_flag: str
    direction: str
    scope_level: str
    scope_ref: str | None = None
    special_rules: list[SpecialTaxRuleInput]
    is_active: bool
    version: int


class TaxCalcLineInput(BaseModel):
    line_id: str
    amount: float = Field(..., ge=0)
    tax_type: str = Field("vat")


class TaxCalculationRequest(BaseModel):
    config_key: str
    lines: list[TaxCalcLineInput]


class TaxCalcLineResultResponse(BaseModel):
    line_id: str
    tax_type: str
    direction: str
    tax_flag: str
    base_amount: float
    tax_amount: float
    total_amount: float


class TaxCalculationResponse(BaseModel):
    config_id: UUID
    config_key: str
    lines: list[TaxCalcLineResultResponse]
    total_tax: float
    total_amount: float