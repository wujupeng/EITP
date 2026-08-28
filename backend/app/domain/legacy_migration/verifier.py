"""迁移校验与回滚 - 行数对比 + 关键字段哈希。

T11-03: 校验失败回滚迁移并保留原数据。
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from enum import Enum
from uuid import UUID

from app.domain.legacy_migration.adapter import LegacyTableData, MigratedTableData


class VerificationStatus(str, Enum):
    """校验状态。"""

    PASSED = "passed"
    FAILED = "failed"


@dataclass
class TableVerificationResult:
    """单表校验结果。"""

    table_name: str
    legacy_row_count: int
    migrated_row_count: int
    legacy_hash: str
    migrated_hash: str
    status: VerificationStatus

    @property
    def row_count_match(self) -> bool:
        return self.legacy_row_count == self.migrated_row_count

    @property
    def hash_match(self) -> bool:
        return self.legacy_hash == self.migrated_hash


@dataclass
class VerificationResult:
    """迁移校验结果。"""

    task_id: UUID
    table_results: list[TableVerificationResult] = field(default_factory=list)
    overall_status: VerificationStatus = VerificationStatus.PASSED

    @property
    def passed_count(self) -> int:
        return sum(1 for r in self.table_results if r.status == VerificationStatus.PASSED)

    @property
    def failed_count(self) -> int:
        return sum(1 for r in self.table_results if r.status == VerificationStatus.FAILED)

    @property
    def all_passed(self) -> bool:
        return self.overall_status == VerificationStatus.PASSED


class MigrationVerifier:
    """迁移校验器 - 行数对比 + 关键字段哈希。

    T11-03: 校验失败回滚迁移并保留原数据。
    """

    @staticmethod
    def compute_hash(rows: list[dict], key_fields: list[str] | None = None) -> str:
        """计算数据行集合的哈希值。

        Args:
            rows: 数据行
            key_fields: 参与哈希的关键字段，None 表示全部字段
        """
        sorted_rows = sorted(
            rows,
            key=lambda r: json.dumps(r, sort_keys=True, default=str),
        )
        if key_fields:
            filtered = [{k: r.get(k) for k in key_fields} for r in sorted_rows]
        else:
            filtered = sorted_rows
        content = json.dumps(filtered, sort_keys=True, default=str)
        return hashlib.sha256(content.encode()).hexdigest()

    @staticmethod
    def verify_table(
        legacy_data: LegacyTableData,
        migrated_data: MigratedTableData,
        key_fields: list[str] | None = None,
    ) -> TableVerificationResult:
        """校验单张表迁移完整性。"""
        legacy_hash = MigrationVerifier.compute_hash(legacy_data.rows, key_fields)
        migrated_rows_for_hash = [
            {k: v for k, v in r.items() if k != "tenant_id"}
            for r in migrated_data.rows
        ]
        migrated_hash = MigrationVerifier.compute_hash(migrated_rows_for_hash, key_fields)

        status = VerificationStatus.PASSED
        if legacy_data.row_count != migrated_data.row_count:
            status = VerificationStatus.FAILED
        elif legacy_hash != migrated_hash:
            status = VerificationStatus.FAILED

        return TableVerificationResult(
            table_name=legacy_data.table_name,
            legacy_row_count=legacy_data.row_count,
            migrated_row_count=migrated_data.row_count,
            legacy_hash=legacy_hash,
            migrated_hash=migrated_hash,
            status=status,
        )

    @staticmethod
    def verify_batch(
        task_id: UUID,
        legacy_batch: list[LegacyTableData],
        migrated_batch: list[MigratedTableData],
        key_fields: list[str] | None = None,
    ) -> VerificationResult:
        """批量校验。"""
        result = VerificationResult(task_id=task_id)

        for legacy, migrated in zip(legacy_batch, migrated_batch):
            table_result = MigrationVerifier.verify_table(legacy, migrated, key_fields)
            result.table_results.append(table_result)

        if any(r.status == VerificationStatus.FAILED for r in result.table_results):
            result.overall_status = VerificationStatus.FAILED

        return result