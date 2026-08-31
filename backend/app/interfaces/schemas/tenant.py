"""租户管理请求/响应 Schema。"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field


class ProvisionTenantRequest(BaseModel):
    enterprise_name: str = Field(..., min_length=1, max_length=255)
    idempotency_key: str = Field(..., min_length=1, max_length=255)
    data_placement: str = Field(default="shared_db")
    admin_email: str = Field(..., description="初始管理员邮箱")
    version: str = Field(default="standard", description="版本")


class TenantResponse(BaseModel):
    id: UUID
    enterprise_name: str
    status: str
    data_placement: str
    version: int
    idempotency_key: str | None


class StatusTransitionRequest(BaseModel):
    action: str = Field(..., description="动作: provision/disable/enable/deprovision")
    confirm_token: str | None = Field(default=None, description="注销确认令牌")