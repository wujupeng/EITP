"""Token 值对象 - Access Token 与 Refresh Token。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class AccessTokenClaims:
    """JWT Access Token 声明。"""

    sub: UUID
    tenant_id: UUID
    jti: str
    iat: datetime
    exp: datetime
    is_platform_admin: bool = False
    is_tenant_admin: bool = False
    roles: tuple[str, ...] = ()
    permissions: tuple[str, ...] = ()


@dataclass(frozen=True)
class RefreshTokenInfo:
    """Refresh Token 信息。"""

    id: UUID
    user_id: UUID
    tenant_id: UUID
    token_hash: str
    expires_at: datetime
    is_revoked: bool = False
    created_at: datetime | None = None
    last_used_at: datetime | None = None


@dataclass(frozen=True)
class TokenPair:
    """Access Token + Refresh Token 对。"""

    access_token: str
    refresh_token: str
    access_token_expires_at: datetime
    refresh_token_expires_at: datetime