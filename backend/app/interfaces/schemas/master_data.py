"""主数据请求/响应 Schema。"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class CreateSkuRequest(BaseModel):
    enterprise_id: UUID
    sku_code: str = Field(..., min_length=1, max_length=255)
    base_attrs: dict[str, Any] = Field(default_factory=dict)


class UpdateBaseRequest(BaseModel):
    base_attrs: dict[str, Any]
    expected_version: int | None = None
    is_group_admin: bool = Field(default=True)


class SetCompanyOverrideRequest(BaseModel):
    organization_id: UUID
    company_attrs: dict[str, Any]
    actor_org_id: UUID | None = None


class SetWarehouseOverrideRequest(BaseModel):
    warehouse_id: UUID
    warehouse_attrs: dict[str, Any]


class MasterDataSkuResponse(BaseModel):
    id: UUID
    enterprise_id: UUID
    sku_code: str
    base_attrs: dict[str, Any]
    version: int


class CompanyOverrideResponse(BaseModel):
    override_id: UUID
    master_data_id: UUID
    organization_id: UUID
    company_attrs: dict[str, Any]
    version: int


class WarehouseOverrideResponse(BaseModel):
    override_id: UUID
    master_data_id: UUID
    warehouse_id: UUID
    warehouse_attrs: dict[str, Any]
    version: int


class EffectiveSkuResponse(BaseModel):
    master_data_id: UUID
    organization_id: UUID | None = None
    warehouse_id: UUID | None = None
    effective_attrs: dict[str, Any]
    base_version: int