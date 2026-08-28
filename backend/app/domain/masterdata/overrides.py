"""主数据覆盖值对象 - 公司级覆盖与仓库级覆盖。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4


@dataclass(frozen=True)
class CompanyOverride:
    """公司级属性覆盖 - 各公司在集团基准上维护的独立属性。

    spec 5.9.1 规则 2：公司级属性不影响集团基准与其他公司。
    """

    override_id: UUID
    master_data_id: UUID
    organization_id: UUID
    company_attrs: dict
    version: int = 0

    @classmethod
    def create(
        cls,
        master_data_id: UUID,
        organization_id: UUID,
        company_attrs: dict,
    ) -> CompanyOverride:
        return cls(
            override_id=uuid4(),
            master_data_id=master_data_id,
            organization_id=organization_id,
            company_attrs=company_attrs,
        )

    def update_attrs(self, new_attrs: dict) -> CompanyOverride:
        """更新公司级属性，返回新实例。"""
        merged = dict(self.company_attrs)
        merged.update(new_attrs)
        return CompanyOverride(
            override_id=self.override_id,
            master_data_id=self.master_data_id,
            organization_id=self.organization_id,
            company_attrs=merged,
            version=self.version + 1,
        )


@dataclass(frozen=True)
class WarehouseOverride:
    """仓库级属性覆盖 - 仓库层维护的库存属性。

    spec 5.9.1 规则 3：仓库级属性继承自公司级并可覆盖。
    """

    override_id: UUID
    master_data_id: UUID
    warehouse_id: UUID
    warehouse_attrs: dict
    version: int = 0

    @classmethod
    def create(
        cls,
        master_data_id: UUID,
        warehouse_id: UUID,
        warehouse_attrs: dict,
    ) -> WarehouseOverride:
        return cls(
            override_id=uuid4(),
            master_data_id=master_data_id,
            warehouse_id=warehouse_id,
            warehouse_attrs=warehouse_attrs,
        )

    def update_attrs(self, new_attrs: dict) -> WarehouseOverride:
        """更新仓库级属性，返回新实例。"""
        merged = dict(self.warehouse_attrs)
        merged.update(new_attrs)
        return WarehouseOverride(
            override_id=self.override_id,
            master_data_id=self.master_data_id,
            warehouse_id=self.warehouse_id,
            warehouse_attrs=merged,
            version=self.version + 1,
        )