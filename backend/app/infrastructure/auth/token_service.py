"""JWT Token 服务 - 签发、验证、刷新 Access Token。

JWT RS256 非对称签名：私钥仅 IAM 持有，公钥分发至所有校验方。
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import jwt
from structlog import get_logger

from app.domain.authn.value_objects.tokens import AccessTokenClaims, TokenPair
from app.infrastructure.auth.jwt_key_manager import get_key_manager
from app.interfaces.middleware.error_handler import IAMError, IAMErrorCode

logger = get_logger(__name__)

ACCESS_TOKEN_TTL = timedelta(minutes=30)
REFRESH_TOKEN_TTL = timedelta(days=7)
REFRESH_TOKEN_ABSOLUTE_MAX = timedelta(days=30)


class TokenService:
    """JWT Token 签发与验证服务。"""

    def __init__(self) -> None:
        self._km = get_key_manager()

    def issue_access_token(
        self,
        user_id: UUID,
        tenant_id: UUID,
        roles: tuple[str, ...] = (),
        permissions: tuple[str, ...] = (),
        is_platform_admin: bool = False,
        is_tenant_admin: bool = False,
    ) -> tuple[str, AccessTokenClaims]:
        now = datetime.now(timezone.utc)
        exp = now + ACCESS_TOKEN_TTL
        jti = secrets.token_urlsafe(32)

        payload = {
            "sub": str(user_id),
            "tenant_id": str(tenant_id),
            "jti": jti,
            "iat": int(now.timestamp()),
            "exp": int(exp.timestamp()),
            "is_platform_admin": is_platform_admin,
            "is_tenant_admin": is_tenant_admin,
            "roles": list(roles),
            "permissions": list(permissions),
        }

        key_pair = self._km.signing_key
        token = jwt.encode(
            payload,
            key_pair.private_key,
            algorithm="RS256",
            headers={"kid": key_pair.key_id},
        )

        claims = AccessTokenClaims(
            sub=user_id,
            tenant_id=tenant_id,
            jti=jti,
            iat=now,
            exp=exp,
            is_platform_admin=is_platform_admin,
            is_tenant_admin=is_tenant_admin,
            roles=roles,
            permissions=permissions,
        )
        return token, claims

    def verify_access_token(self, token: str) -> AccessTokenClaims:
        try:
            unverified_header = jwt.get_unverified_header(token)
            kid = unverified_header.get("kid", "")
            public_key = self._km.get_verification_key(kid)
            payload = jwt.decode(token, public_key, algorithms=["RS256"])
        except jwt.ExpiredSignatureError:
            raise IAMError(IAMErrorCode.TOKEN_EXPIRED, "Token 已过期")
        except jwt.InvalidSignatureError:
            raise IAMError(IAMErrorCode.TOKEN_SIGNATURE_INVALID, "Token 签名无效")
        except jwt.InvalidTokenError as e:
            raise IAMError(IAMErrorCode.TOKEN_SIGNATURE_INVALID, f"Token 无效: {e}")
        except ValueError as e:
            raise IAMError(IAMErrorCode.TOKEN_SIGNATURE_INVALID, f"Token key_id 无效: {e}")

        return AccessTokenClaims(
            sub=UUID(payload["sub"]),
            tenant_id=UUID(payload["tenant_id"]),
            jti=payload["jti"],
            iat=datetime.fromtimestamp(payload["iat"], tz=timezone.utc),
            exp=datetime.fromtimestamp(payload["exp"], tz=timezone.utc),
            is_platform_admin=payload.get("is_platform_admin", False),
            is_tenant_admin=payload.get("is_tenant_admin", False),
            roles=tuple(payload.get("roles", [])),
            permissions=tuple(payload.get("permissions", [])),
        )

    def generate_refresh_token(self) -> tuple[str, str, datetime]:
        """生成 Refresh Token，返回 (raw_token, token_hash, expires_at)。"""
        raw = secrets.token_urlsafe(48)
        token_hash = hashlib.sha256(raw.encode()).hexdigest()
        expires_at = datetime.now(timezone.utc) + REFRESH_TOKEN_TTL
        return raw, token_hash, expires_at

    def hash_refresh_token(self, raw: str) -> str:
        return hashlib.sha256(raw.encode()).hexdigest()

    def issue_token_pair(
        self,
        user_id: UUID,
        tenant_id: UUID,
        roles: tuple[str, ...] = (),
        permissions: tuple[str, ...] = (),
        is_platform_admin: bool = False,
        is_tenant_admin: bool = False,
    ) -> TokenPair:
        access_token, access_claims = self.issue_access_token(
            user_id=user_id,
            tenant_id=tenant_id,
            roles=roles,
            permissions=permissions,
            is_platform_admin=is_platform_admin,
            is_tenant_admin=is_tenant_admin,
        )
        refresh_raw, _, refresh_exp = self.generate_refresh_token()
        return TokenPair(
            access_token=access_token,
            refresh_token=refresh_raw,
            access_token_expires_at=access_claims.exp,
            refresh_token_expires_at=refresh_exp,
        )