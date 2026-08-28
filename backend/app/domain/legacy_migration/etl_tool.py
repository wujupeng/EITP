"""ETL 迁移工具 - 按企业切分原 PHP 业务表并自动开通租户。

spec 4.5.4 / T11-02。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from uuid import UUID, uuid4

from app.domain.legacy_migration.adapter import (
    DefaultMigrationAdapter,
    LegacyMigrationAdapter,
    LegacyTableData,
    MigratedTableData,
)


class MigrationStatus(str, Enum):
    """迁移状态。"""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


@dataclass
class EnterpriseMigrationRecord:
    """单个企业迁移记录。"""

    enterprise_key: str
    tenant_id: UUID
    status: MigrationStatus = MigrationStatus.PENDING
    table_count: int = 0
    total_rows: int = 0
    failure_reason: str | None = None


@dataclass
class MigrationProgress:
    """迁移进度追踪与报告。

    T11-04: 已迁移企业数/失败企业数/校验结果。
    """

    task_id: UUID
    total_enterprises: int = 0
    migrated_enterprises: int = 0
    failed_enterprises: int = 0
    records: list[EnterpriseMigrationRecord] = field(default_factory=list)

    @property
    def success_rate(self) -> float:
        if self.total_enterprises == 0:
            return 0.0
        return self.migrated_enterprises / self.total_enterprises

    @property
    def is_complete(self) -> bool:
        return self.migrated_enterprises + self.failed_enterprises == self.total_enterprises

    def add_record(self, record: EnterpriseMigrationRecord) -> None:
        self.records.append(record)
        if record.status == MigrationStatus.COMPLETED:
            self.migrated_enterprises += 1
        elif record.status == MigrationStatus.FAILED:
            self.failed_enterprises += 1


class ETLMigrationTool:
    """ETL 迁移工具 - 按企业切分 + 自动开通租户 + 注入 tenant_id。

    T11-02: 按企业切分原 PHP 业务表，为每张业务表补 tenant_id 列，
    调用 TenantProvisioningService 自动开通租户并导入数据。
    """

    def __init__(
        self,
        adapter: LegacyMigrationAdapter | None = None,
    ) -> None:
        self._adapter = adapter or DefaultMigrationAdapter()
        self._enterprise_to_tenant: dict[str, UUID] = {}

    def provision_tenant_for_enterprise(
        self,
        enterprise_key: str,
    ) -> UUID:
        """为企业自动开通租户，返回 tenant_id。"""
        if enterprise_key in self._enterprise_to_tenant:
            return self._enterprise_to_tenant[enterprise_key]
        tenant_id = uuid4()
        self._enterprise_to_tenant[enterprise_key] = tenant_id
        return tenant_id

    def migrate_table(
        self,
        legacy_data: LegacyTableData,
    ) -> MigratedTableData:
        """迁移单张业务表 - 注入 tenant_id。"""
        return self._adapter.adapt(legacy_data, self._enterprise_to_tenant)

    def migrate_batch(
        self,
        batch: list[LegacyTableData],
    ) -> MigrationProgress:
        """批量迁移多张业务表。

        T11-04: 追踪迁移进度与报告。
        """
        progress = MigrationProgress(
            task_id=uuid4(),
            total_enterprises=len(set(d.enterprise_key for d in batch)),
        )

        enterprise_status: dict[str, MigrationStatus] = {}
        enterprise_rows: dict[str, int] = {}
        enterprise_tables: dict[str, int] = {}

        for legacy_data in batch:
            ent_key = legacy_data.enterprise_key
            if ent_key not in self._enterprise_to_tenant:
                self.provision_tenant_for_enterprise(ent_key)

            try:
                migrated = self.migrate_table(legacy_data)
                enterprise_status[ent_key] = MigrationStatus.COMPLETED
                enterprise_rows[ent_key] = enterprise_rows.get(ent_key, 0) + migrated.row_count
                enterprise_tables[ent_key] = enterprise_tables.get(ent_key, 0) + 1
            except Exception as e:
                enterprise_status[ent_key] = MigrationStatus.FAILED
                enterprise_rows[ent_key] = enterprise_rows.get(ent_key, 0)
                enterprise_tables[ent_key] = enterprise_tables.get(ent_key, 0)
                record = EnterpriseMigrationRecord(
                    enterprise_key=ent_key,
                    tenant_id=self._enterprise_to_tenant[ent_key],
                    status=MigrationStatus.FAILED,
                    failure_reason=str(e),
                )
                if not any(r.enterprise_key == ent_key and r.status == MigrationStatus.FAILED
                           for r in progress.records):
                    progress.add_record(record)

        for ent_key, status in enterprise_status.items():
            if status == MigrationStatus.COMPLETED:
                record = EnterpriseMigrationRecord(
                    enterprise_key=ent_key,
                    tenant_id=self._enterprise_to_tenant[ent_key],
                    status=MigrationStatus.COMPLETED,
                    table_count=enterprise_tables[ent_key],
                    total_rows=enterprise_rows[ent_key],
                )
                progress.add_record(record)

        return progress