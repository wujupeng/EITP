"""IAM 请求/响应 Schema。"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    tenant_id: UUID = Field(..., description="租户 ID")
    username: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=1, max_length=255)


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int = 1800
    user_id: UUID
    username: str
    tenant_id: UUID
    is_platform_admin: bool = False
    is_tenant_admin: bool = False


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class ChangePasswordRequest(BaseModel):
    old_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=12, max_length=255)


class LogoutRequest(BaseModel):
    refresh_token: str | None = None


class UserCreateRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=12, max_length=255)
    email: str | None = None
    phone: str | None = None
    real_name: str | None = None
    is_tenant_admin: bool = False


class UserResponse(BaseModel):
    id: UUID
    username: str
    email: str | None = None
    phone: str | None = None
    real_name: str | None = None
    account_status: str
    is_platform_admin: bool = False
    is_tenant_admin: bool = False
    last_login_at: str | None = None


class MeResponse(BaseModel):
    user_id: UUID
    username: str
    tenant_id: UUID
    email: str | None = None
    roles: list[str] = []
    permissions: list[str] = []
    is_platform_admin: bool = False
    is_tenant_admin: bool = False