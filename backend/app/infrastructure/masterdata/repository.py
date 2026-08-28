"""主数据仓储 - 基准与覆盖的持久化。"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.masterdata.master_data_base import MasterDataBase
from app.domain.masterdata.overrides import CompanyOverride, WarehouseOverride
from app.domain.shared.entity import EntityId
from app.infrastructure.masterdata.models import (
    CompanyOverrideORM,
    MasterDataBaseORM,
    WarehouseOverrideORM,
)


class MasterDataRepository:
    """主数据仓储。"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save_base(self, base: MasterDataBase) -> None:
        """保存主数据基准（upsert）。"""
        stmt = pg_insert(MasterDataBaseORM).values(
            id=base.id.value,
            enterprise_id=base.enterprise_id,
            sku_code=base.sku_code,
            base_attrs=base.base_attrs,
            version=base.version,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["enterprise_id", "sku_code"],
            set_={
                "base_attrs": stmt.excluded.base_attrs,
                "version": stmt.excluded.version,
            },
        )
        await self._session.execute(stmt)

    async def get_base_by_id(self, master_data_id: UUID) -> MasterDataBase | None:
        stmt = select(MasterDataBaseORM).where(MasterDataBaseORM.id == master_data_id)
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        if orm is None:
            return None
        return MasterDataBase(
            id=EntityId(orm.id),
            enterprise_id=orm.enterprise_id,
            sku_code=orm.sku_code,
            base_attrs=orm.base_attrs,
            version=orm.version,
        )

    async def get_base_by_code(
        self, enterprise_id: UUID, sku_code: str
    ) -> MasterDataBase | None:
        stmt = select(MasterDataBaseORM).where(
            MasterDataBaseORM.enterprise_id == enterprise_id,
            MasterDataBaseORM.sku_code == sku_code,
        )
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        if orm is None:
            return None
        return MasterDataBase(
            id=EntityId(orm.id),
            enterprise_id=orm.enterprise_id,
            sku_code=orm.sku_code,
            base_attrs=orm.base_attrs,
            version=orm.version,
        )

    async def save_company_override(self, override: CompanyOverride) -> None:
        stmt = pg_insert(CompanyOverrideORM).values(
            override_id=override.override_id,
            master_data_id=override.master_data_id,
            organization_id=override.organization_id,
            company_attrs=override.company_attrs,
            version=override.version,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["master_data_id", "organization_id"],
            set_={
                "company_attrs": stmt.excluded.company_attrs,
                "version": stmt.excluded.version,
            },
        )
        await self._session.execute(stmt)

    async def get_company_override(
        self, master_data_id: UUID, organization_id: UUID
    ) -> CompanyOverride | None:
        stmt = select(CompanyOverrideORM).where(
            CompanyOverrideORM.master_data_id == master_data_id,
            CompanyOverrideORM.organization_id == organization_id,
        )
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        if orm is None:
            return None
        return CompanyOverride(
            override_id=orm.override_id,
            master_data_id=orm.master_data_id,
            organization_id=orm.organization_id,
            company_attrs=orm.company_attrs,
            version=orm.version,
        )

    async def save_warehouse_override(self, override: WarehouseOverride) -> None:
        stmt = pg_insert(WarehouseOverrideORM).values(
            override_id=override.override_id,
            master_data_id=override.master_data_id,
            warehouse_id=override.warehouse_id,
            warehouse_attrs=override.warehouse_attrs,
            version=override.version,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["master_data_id", "warehouse_id"],
            set_={
                "warehouse_attrs": stmt.excluded.warehouse_attrs,
                "version": stmt.excluded.version,
            },
        )
        await self._session.execute(stmt)

    async def get_warehouse_override(
        self, master_data_id: UUID, warehouse_id: UUID
    ) -> WarehouseOverride | None:
        stmt = select(WarehouseOverrideORM).where(
            WarehouseOverrideORM.master_data_id == master_data_id,
            WarehouseOverrideORM.warehouse_id == warehouse_id,
        )
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        if orm is None:
            return None
        return WarehouseOverride(
            override_id=orm.override_id,
            master_data_id=orm.master_data_id,
            warehouse_id=orm.warehouse_id,
            warehouse_attrs=orm.warehouse_attrs,
            version=orm.version,
        )