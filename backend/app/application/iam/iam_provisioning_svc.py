"""IAM 初始化服务 - 租户开通时创建初始管理员与内置角色。

T13: MT-001 集成 - 控制面 ProvisioningOrchestrator 调用此服务。
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.application.iam.user_app_svc import UserAppSvc
from app.domain.authz.aggregates.role_aggregate import RoleAggregate, BuiltinRole
from app.domain.authz.entities.permission import Permission, BUILTIN_PERMISSIONS
from app.domain.policy.aggregates.password_policy_aggregate import (
    PasswordPolicyAggregate,
    PolicyScope,
)
from app.infrastructure.authz.permission_repository import PermissionRepository
from app.infrastructure.authz.role_repository import RoleRepository
from app.infrastructure.policy.password_policy_repository import PasswordPolicyRepository


class IamProvisioningSvc:
    """IAM 开通服务 - 租户开通时初始化 IAM 资源。"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._user_svc = UserAppSvc(session)
        self._role_repo = RoleRepository(session)
        self._perm_repo = PermissionRepository(session)
        self._policy_repo = PasswordPolicyRepository(session)

    async def provision_tenant_iam(
        self,
        tenant_id: UUID,
        admin_username: str = "admin",
        admin_password: str = "Admin123!@#change",
        admin_email: str | None = None,
    ) -> dict:
        """租户开通时初始化 IAM 资源。

        1. 创建租户级密码策略
        2. 创建内置权限定义
        3. 创建内置角色
        4. 创建初始管理员用户
        5. 分配管理员角色
        """
        policy = PasswordPolicyAggregate.tenant_default(tenant_id)
        await self._policy_repo.save(policy)

        permissions: list[Permission] = []
        for perm_def in BUILTIN_PERMISSIONS:
            perm = Permission.create(**perm_def)
            try:
                await self._perm_repo.save(perm)
                permissions.append(perm)
            except Exception:
                pass

        roles: list[RoleAggregate] = []
        for builtin in BuiltinRole:
            role = RoleAggregate.builtin(tenant_id=tenant_id, role=builtin)
            if builtin == BuiltinRole.TENANT_ADMIN:
                role.permission_ids = {p.id for p in permissions}
            elif builtin == BuiltinRole.ENTERPRISE_ADMIN:
                role.permission_ids = {
                    p.id for p in permissions
                    if "read" in p.code or "write" in p.code
                }
            elif builtin == BuiltinRole.BUSINESS_USER:
                role.permission_ids = {
                    p.id for p in permissions if "read" in p.code
                }
            try:
                await self._role_repo.save(role)
                roles.append(role)
            except Exception:
                pass

        admin_user = await self._user_svc.create_user(
            tenant_id=tenant_id,
            username=admin_username,
            password=admin_password,
            email=admin_email,
            is_tenant_admin=True,
        )

        tenant_admin_role = next(
            (r for r in roles if r.role_code == BuiltinRole.TENANT_ADMIN.value), None
        )
        if tenant_admin_role:
            await self._role_repo.assign_to_user(admin_user.id.value, tenant_admin_role.id)

        await self._session.commit()

        return {
            "tenant_id": str(tenant_id),
            "admin_user_id": str(admin_user.id.value),
            "admin_username": admin_username,
            "roles_created": len(roles),
            "permissions_created": len(permissions),
        }