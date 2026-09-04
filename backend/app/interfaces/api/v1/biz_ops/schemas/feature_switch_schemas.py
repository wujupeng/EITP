"""BIZ-OPS 功能开关 Schema。"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field


class FeatureSwitchUpdateRequest(BaseModel):
    is_enabled: bool = Field(..., description="开关状态")
    description: str | None = Field(None, max_length=500, description="描述")


class FeatureSwitchCreateRequest(BaseModel):
    feature_key: str = Field(..., max_length=100, description="功能键")
    scope: str = Field(..., max_length=20, description="作用域: module/sub_feature")
    is_enabled: bool = Field(True, description="开关状态")
    parent_feature_key: str | None = Field(None, max_length=100, description="父功能键")
    description: str | None = Field(None, max_length=500, description="描述")


class FeatureSwitchResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    feature_key: str
    scope: str
    is_enabled: bool
    parent_feature_key: str | None = None
    description: str | None = None
    effective_is_enabled: bool = True


class BizOpsResponse(BaseModel):
    """通用响应包装。"""
    success: bool = True
    message: str = ""
    data: dict | list | None = None