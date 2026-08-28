"""LegacyMigrationAdapter 契约 - 原 PHP 系统数据到多租户数据的映射。

spec 4.5.4: 不在本仓库实现 PHP 端，仅定义接口契约。
输入原 PHP 业务表数据（无 tenant_id），输出按企业映射为独立 Tenant 的迁移数据（自动注入 tenant_id）。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from uuid import UUID


@dataclass(frozen=True)
class LegacyTableData:
    """原 PHP 业务表数据 - 无 tenant_id 列。"""

    table_name: str
    enterprise_key: str
    rows: list[dict] = field(default_factory=list)

    @property
    def row_count(self) -> int:
        return len(self.rows)


@dataclass(frozen=True)
class MigratedTableData:
    """迁移后数据 - 已注入 tenant_id。"""

    table_name: str
    tenant_id: UUID
    rows: list[dict] = field(default_factory=list)

    @property
    def row_count(self) -> int:
        return len(self.rows)


class LegacyMigrationAdapter(ABC):
    """存量迁移适配器契约 - 按企业映射为独立 Tenant。"""

    @abstractmethod
    def adapt(
        self,
        legacy_data: LegacyTableData,
        enterprise_to_tenant: dict[str, UUID],
    ) -> MigratedTableData:
        """将原 PHP 数据转换为多租户数据。"""
        ...


class DefaultMigrationAdapter(LegacyMigrationAdapter):
    """默认迁移适配器实现 - 注入 tenant_id 列。"""

    def adapt(
        self,
        legacy_data: LegacyTableData,
        enterprise_to_tenant: dict[str, UUID],
    ) -> MigratedTableData:
        tenant_id = enterprise_to_tenant.get(legacy_data.enterprise_key)
        if tenant_id is None:
            raise ValueError(
                f"企业 {legacy_data.enterprise_key} 未找到对应的租户映射"
            )

        migrated_rows = [
            {**row, "tenant_id": str(tenant_id)}
            for row in legacy_data.rows
        ]

        return MigratedTableData(
            table_name=legacy_data.table_name,
            tenant_id=tenant_id,
            rows=migrated_rows,
        )