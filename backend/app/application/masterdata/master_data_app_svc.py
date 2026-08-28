"""MasterDataAppSvc - 主数据应用服务，编排聚合根与仓储。"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.masterdata.master_data_base import MasterDataBase
from app.domain.masterdata.overrides import CompanyOverride, WarehouseOverride
from app.domain.masterdata.permission_guard import MasterDataPermissionGuard
from app.domain.shared.entity import EntityId
from app.infrastructure.masterdata.repository import MasterDataRepository
from app.interfaces.middleware.error_handler import ErrorCode, GroupError


class MasterDataAppSvc:
    """主数据应用服务 - 三层继承 CRUD 与合并求值。"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = MasterDataRepository(session)

    async def create_base(
        self,
        enterprise_id: UUID,
        sku_code: str,
        base_attrs: dict,
    ) -> MasterDataBase:
        """创建集团主数据基准。"""
        existing = await self._repo.get_base_by_code(enterprise_id, sku_code)
        if existing is not None:
            raise GroupError(
                ErrorCode.MASTER_DATA_CONFLICT,
                f"SKU 编码 {sku_code} 已存在",
            )

        base = MasterDataBase(
            id=EntityId.generate(),
            enterprise_id=enterprise_id,
            sku_code=sku_code,
            base_attrs=base_attrs,
        )
        base.record_created_event()
        await self._repo.save_base(base)
        await self._session.commit()
        return base

    async def update_base(
        self,
        master_data_id: UUID,
        new_attrs: dict,
        expected_version: int | None = None,
        is_group_admin: bool = True,
    ) -> MasterDataBase:
        """更新集团基准属性（仅集团管理员）。"""
        MasterDataPermissionGuard.enforce_base_write(
            is_group_admin, UUID(int=0), master_data_id
        )

        base = await self._repo.get_base_by_id(master_data_id)
        if base is None:
            raise GroupError(ErrorCode.MASTER_NOT_FOUND, "主数据基准不存在")

        base.update_base_attrs(new_attrs, expected_version)
        await self._repo.save_base(base)
        await self._session.commit()
        return base

    async def set_company_override(
        self,
        master_data_id: UUID,
        organization_id: UUID,
        company_attrs: dict,
        actor_org_id: UUID | None = None,
    ) -> CompanyOverride:
        """设置公司级属性覆盖。"""
        base = await self._repo.get_base_by_id(master_data_id)
        if base is None:
            raise GroupError(ErrorCode.MASTER_NOT_FOUND, "主数据基准不存在")

        if actor_org_id is not None:
            MasterDataPermissionGuard.enforce_company_override_write(
                actor_org_id, organization_id
            )

        existing = await self._repo.get_company_override(master_data_id, organization_id)
        if existing is not None:
            override = existing.update_attrs(company_attrs)
        else:
            override = CompanyOverride.create(
                master_data_id=master_data_id,
                organization_id=organization_id,
                company_attrs=company_attrs,
            )

        base.set_company_override(override)
        await self._repo.save_company_override(override)
        await self._session.commit()
        return override

    async def set_warehouse_override(
        self,
        master_data_id: UUID,
        warehouse_id: UUID,
        warehouse_attrs: dict,
    ) -> WarehouseOverride:
        """设置仓库级属性覆盖。"""
        base = await self._repo.get_base_by_id(master_data_id)
        if base is None:
            raise GroupError(ErrorCode.MASTER_NOT_FOUND, "主数据基准不存在")

        existing = await self._repo.get_warehouse_override(master_data_id, warehouse_id)
        if existing is not None:
            override = existing.update_attrs(warehouse_attrs)
        else:
            override = WarehouseOverride.create(
                master_data_id=master_data_id,
                warehouse_id=warehouse_id,
                warehouse_attrs=warehouse_attrs,
            )

        base.set_warehouse_override(override)
        await self._repo.save_warehouse_override(override)
        await self._session.commit()
        return override

    async def get_effective_attrs(
        self,
        master_data_id: UUID,
        organization_id: UUID | None = None,
        warehouse_id: UUID | None = None,
    ) -> dict:
        """三层合并求值：base ∪ company ∪ warehouse。"""
        base = await self._repo.get_base_by_id(master_data_id)
        if base is None:
            raise GroupError(ErrorCode.MASTER_NOT_FOUND, "主数据基准不存在")

        if organization_id is not None:
            override = await self._repo.get_company_override(
                master_data_id, organization_id
            )
            if override is not None:
                base.set_company_override(override)

        if warehouse_id is not None:
            override = await self._repo.get_warehouse_override(
                master_data_id, warehouse_id
            )
            if override is not None:
                base.set_warehouse_override(override)

        return base.effective_attrs(organization_id, warehouse_id)