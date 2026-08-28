"""TenantAppSvc - 租户应用服务，编排领域层与仓储层。"""

from __future__ import annotations

from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.shared.entity import EntityId
from app.domain.tenant.tenant_aggregate import TenantAggregate
from app.domain.tenant.tenant_state import DataPlacement, TenantStatus
from app.infrastructure.tenant.repository import TenantRepository
from app.interfaces.middleware.error_handler import DomainError, ErrorCode


class TenantAppSvc:
    """租户应用服务 - 平台运营操作。"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = TenantRepository(session)

    async def provision(
        self,
        enterprise_name: str,
        idempotency_key: str,
        data_placement: DataPlacement = DataPlacement.SHARED_DB,
    ) -> TenantAggregate:
        """开通租户 - 幂等控制。"""
        existing = await self._repo.get_by_idempotency_key(idempotency_key)
        if existing is not None:
            raise DomainError(
                ErrorCode.TENANT_ALREADY_EXISTS,
                "租户已存在（幂等键重复）",
            )

        tenant = TenantAggregate(
            id=EntityId.generate(),
            enterprise_name=enterprise_name,
            idempotency_key=idempotency_key,
            data_placement=data_placement,
        )
        await self._repo.save(tenant)
        await self._session.commit()
        return tenant

    async def complete_provision(self, tenant_id: UUID) -> TenantAggregate:
        """完成开通流程。"""
        tenant = await self._repo.get_by_id(tenant_id)
        if tenant is None:
            raise DomainError(ErrorCode.TENANT_CONTEXT_INVALID, "租户不存在")
        tenant.provision()
        await self._repo.update_status(tenant_id, tenant.status)
        await self._session.commit()
        return tenant

    async def disable(self, tenant_id: UUID) -> TenantAggregate:
        """停用租户。"""
        tenant = await self._repo.get_by_id(tenant_id)
        if tenant is None:
            raise DomainError(ErrorCode.TENANT_CONTEXT_INVALID, "租户不存在")
        tenant.disable()
        await self._repo.update_status(tenant_id, tenant.status)
        await self._session.commit()
        return tenant

    async def enable(self, tenant_id: UUID) -> TenantAggregate:
        """恢复租户。"""
        tenant = await self._repo.get_by_id(tenant_id)
        if tenant is None:
            raise DomainError(ErrorCode.TENANT_CONTEXT_INVALID, "租户不存在")
        tenant.enable()
        await self._repo.update_status(tenant_id, tenant.status)
        await self._session.commit()
        return tenant

    async def deprovision(
        self,
        tenant_id: UUID,
        confirm_token: str | None = None,
    ) -> TenantAggregate:
        """注销租户 - 需二次确认。"""
        tenant = await self._repo.get_by_id(tenant_id)
        if tenant is None:
            raise DomainError(ErrorCode.TENANT_CONTEXT_INVALID, "租户不存在")
        tenant.deprovision(confirm_token)
        await self._repo.update_status(tenant_id, tenant.status)
        await self._session.commit()
        return tenant

    async def get_tenant(self, tenant_id: UUID) -> TenantAggregate | None:
        return await self._repo.get_by_id(tenant_id)

    async def list_tenants(self, offset: int = 0, limit: int = 50) -> list[TenantAggregate]:
        return await self._repo.list_all(offset, limit)