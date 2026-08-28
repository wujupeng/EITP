"""主数据基准聚合根 - 集团层统一主数据，含乐观锁。

spec 5.9 / design 2.3.2.4。
三层继承：集团基准（base_attrs） → 公司级覆盖（company_attrs） → 仓库级覆盖（warehouse_attrs）
最终生效值：EffectiveSku = base_attrs ∪ company_attrs ∪ warehouse_attrs（后者覆盖前者同名键）
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.domain.masterdata.master_data_events import (
    CompanyOverrideUpdatedEvent,
    MasterDataBaseChangedEvent,
    MasterDataBaseCreatedEvent,
    WarehouseOverrideUpdatedEvent,
)
from app.domain.masterdata.overrides import CompanyOverride, WarehouseOverride
from app.domain.shared.aggregate_root import AggregateRoot
from app.domain.shared.entity import EntityId
from app.interfaces.middleware.error_handler import ErrorCode, GroupError


class MasterDataBase(AggregateRoot):
    """主数据基准聚合根 - 集团层统一主数据。

    职责：
    - 维护 base_attrs 与 version（乐观锁）
    - 管理公司级覆盖与仓库级覆盖
    - 三层合并求值（effective_attrs）
    - 变更下发（递增 version）
    """

    def __init__(
        self,
        id: EntityId,
        enterprise_id: UUID,
        sku_code: str,
        base_attrs: dict | None = None,
        version: int = 1,
    ) -> None:
        super().__init__(id)
        self._enterprise_id = enterprise_id
        self._sku_code = sku_code
        self._base_attrs = dict(base_attrs or {})
        self._version = version
        self._company_overrides: dict[UUID, CompanyOverride] = {}
        self._warehouse_overrides: dict[UUID, WarehouseOverride] = {}

    @property
    def enterprise_id(self) -> UUID:
        return self._enterprise_id

    @property
    def sku_code(self) -> str:
        return self._sku_code

    @property
    def base_attrs(self) -> dict:
        return dict(self._base_attrs)

    @property
    def version(self) -> int:
        return self._version

    def update_base_attrs(
        self,
        new_attrs: dict,
        expected_version: int | None = None,
    ) -> None:
        """更新集团基准属性，递增 version（乐观锁）。

        Args:
            new_attrs: 新属性（合并到现有）
            expected_version: 乐观锁期望版本号

        Raises:
            GroupError: 乐观锁版本不匹配
        """
        if expected_version is not None and expected_version != self._version:
            raise GroupError(
                ErrorCode.MASTER_ATTR_CONFLICT,
                f"乐观锁版本不匹配：期望 {expected_version}，实际 {self._version}",
            )

        old_version = self._version
        self._base_attrs.update(new_attrs)
        self._version += 1
        self._touch()

        self._record_event(
            MasterDataBaseChangedEvent(
                enterprise_id=self._enterprise_id,
                master_data_id=self._id.value,
                sku_code=self._sku_code,
                old_version=old_version,
                new_version=self._version,
            )
        )

    def set_company_override(self, override: CompanyOverride) -> None:
        """设置/更新公司级覆盖。"""
        if override.master_data_id != self._id.value:
            raise GroupError(
                ErrorCode.MASTER_ATTR_CONFLICT,
                "覆盖的 master_data_id 与基准不匹配",
            )
        existing = self._company_overrides.get(override.organization_id)
        changed_keys = tuple(override.company_attrs.keys())
        self._company_overrides[override.organization_id] = override
        self._record_event(
            CompanyOverrideUpdatedEvent(
                master_data_id=self._id.value,
                organization_id=override.organization_id,
                changed_keys=changed_keys,
            )
        )

    def set_warehouse_override(self, override: WarehouseOverride) -> None:
        """设置/更新仓库级覆盖。"""
        if override.master_data_id != self._id.value:
            raise GroupError(
                ErrorCode.MASTER_ATTR_CONFLICT,
                "覆盖的 master_data_id 与基准不匹配",
            )
        changed_keys = tuple(override.warehouse_attrs.keys())
        self._warehouse_overrides[override.warehouse_id] = override
        self._record_event(
            WarehouseOverrideUpdatedEvent(
                master_data_id=self._id.value,
                warehouse_id=override.warehouse_id,
                changed_keys=changed_keys,
            )
        )

    def get_company_override(self, organization_id: UUID) -> CompanyOverride | None:
        return self._company_overrides.get(organization_id)

    def get_warehouse_override(self, warehouse_id: UUID) -> WarehouseOverride | None:
        return self._warehouse_overrides.get(warehouse_id)

    def effective_attrs(
        self,
        organization_id: UUID | None = None,
        warehouse_id: UUID | None = None,
    ) -> dict:
        """三层合并求值：base ∪ company ∪ warehouse。

        后者覆盖前者同名键。
        """
        result = dict(self._base_attrs)

        if organization_id is not None:
            company = self._company_overrides.get(organization_id)
            if company is not None:
                result.update(company.company_attrs)

        if warehouse_id is not None:
            warehouse = self._warehouse_overrides.get(warehouse_id)
            if warehouse is not None:
                result.update(warehouse.warehouse_attrs)

        return result

    def record_created_event(self) -> None:
        """记录基准创建事件。"""
        self._record_event(
            MasterDataBaseCreatedEvent(
                enterprise_id=self._enterprise_id,
                master_data_id=self._id.value,
                sku_code=self._sku_code,
                version=self._version,
            )
        )