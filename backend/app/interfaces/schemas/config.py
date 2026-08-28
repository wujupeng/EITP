"""配置管理请求/响应 Schema。"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class SetConfigRequest(BaseModel):
    config_key: str = Field(..., min_length=1, max_length=255)
    value: Any
    is_overridden: bool = Field(default=True)
    scope_level: str = Field(default="tenant")


class ConfigResponse(BaseModel):
    config_key: str
    value: Any
    is_overridden: bool
    scope_level: str
    resolved_value: Any | None = None


class SetFeatureFlagRequest(BaseModel):
    feature_key: str = Field(..., min_length=1, max_length=255)
    enabled: bool


class FeatureFlagResponse(BaseModel):
    tenant_id: UUID
    feature_key: str
    enabled: bool