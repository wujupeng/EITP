"""认证应用服务 - 登录/登出/刷新/改密/me。"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.audit.aggregates.login_audit_aggregate import LoginAuditEntry, LoginAction
from app.domain.identity.aggregates.user_aggregate import AccountStatus, UserAggregate
from app.domain.policy.aggregates.password_policy_aggregate import PasswordPolicyAggregate
from app.domain.policy.services.password_hasher import get_password_hasher
from app.domain.policy.services.password_strength_validator import PasswordStrengthValidator
from app.infrastructure.audit.brute_force_service import BruteForceService
from app.infrastructure.audit.login_audit_repository import LoginAuditRepository
from app.infrastructure.auth.refresh_token_repository import RefreshTokenRepository
from app.infrastructure.auth.token_revocation_service import get_revocation_service
from app.infrastructure.auth.token_service import TokenService
from app.infrastructure.identity.user_repository import UserRepository
from app.infrastructure.policy.password_history_repository import PasswordHistoryRepository
from app.infrastructure.policy.password_policy_repository import PasswordPolicyRepository
from app.interfaces.middleware.error_handler import IAMError, IAMErrorCode


class AuthAppSvc:
    """认证应用服务。"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._user_repo = UserRepository(session)
        self._token_svc = TokenService()
        self._refresh_repo = RefreshTokenRepository(session)
        self._revocation_svc = get_revocation_service()
        self._audit_repo = LoginAuditRepository(session)
        self._brute_force = BruteForceService()
        self._hasher = get_password_hasher()
        self._validator = PasswordStrengthValidator()
        self._policy_repo = PasswordPolicyRepository(session)
        self._history_repo = PasswordHistoryRepository(session)

    async def login(
        self,
        tenant_id: UUID,
        username: str,
        password: str,
        ip_address: str = "",
        user_agent: str = "",
    ) -> dict:
        """用户登录。"""
        if await self._brute_force.is_ip_banned(ip_address):
            raise IAMError(IAMErrorCode.IP_BANNED, "IP 已被封禁")

        user = await self._user_repo.find_by_tenant_username(tenant_id, username)

        if user is None:
            await self._brute_force.record_failure(username, ip_address)
            await self._audit_repo.add(LoginAuditEntry(
                tenant_id=tenant_id, username=username, action=LoginAction.LOGIN,
                success=False, ip_address=ip_address, user_agent=user_agent,
                failure_reason="user_not_found",
            ))
            raise IAMError(IAMErrorCode.CREDENTIAL_INVALID, "用户名或密码错误")

        if await self._brute_force.is_account_locked(username):
            raise IAMError(IAMErrorCode.ACCOUNT_LOCKED, "账号已锁定，请稍后再试")

        if user.account_status == AccountStatus.DISABLED:
            raise IAMError(IAMErrorCode.ACCOUNT_LOCKED, "账号已停用")

        if user.account_status == AccountStatus.DEACTIVATED:
            raise IAMError(IAMErrorCode.CREDENTIAL_INVALID, "用户名或密码错误")

        if not user.verify_password(password, self._hasher):
            locked, _ = await self._brute_force.record_failure(username, ip_address)
            if locked:
                user.lock(15)
                await self._user_repo.update(user)
            await self._audit_repo.add(LoginAuditEntry(
                tenant_id=tenant_id, user_id=user.id.value, username=username,
                action=LoginAction.LOGIN, success=False, ip_address=ip_address,
                user_agent=user_agent, failure_reason="wrong_password",
            ))
            await self._session.commit()
            raise IAMError(IAMErrorCode.CREDENTIAL_INVALID, "用户名或密码错误")

        if user.account_status == AccountStatus.PENDING_ACTIVATION:
            user.activate()

        user.record_login(ip_address)
        await self._user_repo.update(user)
        await self._brute_force.reset_account(username)

        token_pair = self._token_svc.issue_token_pair(
            user_id=user.id.value,
            tenant_id=tenant_id,
            is_platform_admin=user.is_platform_admin,
            is_tenant_admin=user.is_tenant_admin,
        )

        from app.domain.authn.value_objects.tokens import RefreshTokenInfo
        from uuid import uuid4
        refresh_hash = self._token_svc.hash_refresh_token(token_pair.refresh_token)
        await self._refresh_repo.save(RefreshTokenInfo(
            id=uuid4(),
            user_id=user.id.value,
            tenant_id=tenant_id,
            token_hash=refresh_hash,
            expires_at=token_pair.refresh_token_expires_at,
        ))

        await self._audit_repo.add(LoginAuditEntry(
            tenant_id=tenant_id, user_id=user.id.value, username=username,
            action=LoginAction.LOGIN, success=True, ip_address=ip_address,
            user_agent=user_agent,
        ))
        await self._session.commit()

        return {
            "access_token": token_pair.access_token,
            "refresh_token": token_pair.refresh_token,
            "token_type": "Bearer",
            "expires_in": 1800,
            "user_id": str(user.id.value),
            "username": user.username,
            "tenant_id": str(tenant_id),
            "is_platform_admin": user.is_platform_admin,
            "is_tenant_admin": user.is_tenant_admin,
        }

    async def logout(self, access_token: str, refresh_token: str | None = None) -> None:
        """用户登出。"""
        try:
            claims = self._token_svc.verify_access_token(access_token)
            await self._revocation_svc.revoke_token(
                jti=claims.jti,
                user_id=str(claims.sub),
                reason="logout",
                expires_at=claims.exp,
            )
        except Exception:
            pass

        if refresh_token:
            refresh_hash = self._token_svc.hash_refresh_token(refresh_token)
            info = await self._refresh_repo.get_by_hash(refresh_hash)
            if info and not info.is_revoked:
                await self._refresh_repo.revoke(info.id)

        await self._session.commit()

    async def refresh(self, refresh_token: str) -> dict:
        """刷新 Access Token。"""
        token_hash = self._token_svc.hash_refresh_token(refresh_token)
        info = await self._refresh_repo.get_by_hash(token_hash)

        if info is None or info.is_revoked:
            raise IAMError(IAMErrorCode.REFRESH_TOKEN_REVOKED, "Refresh Token 无效或已撤销")

        if datetime.now(timezone.utc) > info.expires_at:
            raise IAMError(IAMErrorCode.TOKEN_EXPIRED, "Refresh Token 已过期")

        await self._refresh_repo.revoke(info.id)

        user = await self._user_repo.get_by_id(info.user_id)
        if user is None or user.account_status != AccountStatus.ACTIVE:
            raise IAMError(IAMErrorCode.CREDENTIAL_INVALID, "用户状态异常")

        token_pair = self._token_svc.issue_token_pair(
            user_id=user.id.value,
            tenant_id=info.tenant_id,
            is_platform_admin=user.is_platform_admin,
            is_tenant_admin=user.is_tenant_admin,
        )

        from app.domain.authn.value_objects.tokens import RefreshTokenInfo
        from uuid import uuid4
        new_hash = self._token_svc.hash_refresh_token(token_pair.refresh_token)
        await self._refresh_repo.save(RefreshTokenInfo(
            id=uuid4(),
            user_id=user.id.value,
            tenant_id=info.tenant_id,
            token_hash=new_hash,
            expires_at=token_pair.refresh_token_expires_at,
        ))
        await self._session.commit()

        return {
            "access_token": token_pair.access_token,
            "refresh_token": token_pair.refresh_token,
            "token_type": "Bearer",
            "expires_in": 1800,
        }

    async def change_password(
        self,
        user_id: UUID,
        old_password: str,
        new_password: str,
    ) -> None:
        """修改密码。"""
        user = await self._user_repo.get_by_id(user_id)
        if user is None:
            raise IAMError(IAMErrorCode.USER_NOT_FOUND, "用户不存在")

        policy = await self._policy_repo.get_tenant(user.tenant_id)
        if policy is None:
            policy = PasswordPolicyAggregate.tenant_default(user.tenant_id)

        is_reused = await self._history_repo.is_reused(
            user_id, self._hasher.hash(new_password).hash, policy.history_count
        )

        user.change_password(old_password, new_password, self._hasher, self._validator, policy, is_reused)
        await self._user_repo.update(user)

        await self._history_repo.add(user.id.value, user.password_hash, user.password_salt)
        await self._history_repo.prune_old(user.id.value, policy.history_count)

        await self._revocation_svc.revoke_all_user_tokens(str(user_id))
        await self._session.commit()

    async def get_me(self, user_id: UUID) -> dict:
        """获取当前登录用户信息。"""
        user = await self._user_repo.get_by_id(user_id)
        if user is None:
            raise IAMError(IAMErrorCode.USER_NOT_FOUND, "用户不存在")

        return {
            "user_id": str(user.id.value),
            "username": user.username,
            "tenant_id": str(user.tenant_id),
            "email": user.email,
            "is_platform_admin": user.is_platform_admin,
            "is_tenant_admin": user.is_tenant_admin,
            "roles": [],
            "permissions": [],
        }