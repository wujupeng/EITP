"""LegacyMigration Bounded Context - 存量 PHP 数据迁移。

spec 4.5.4 / design 1.2.1: 原 PHP 单租户系统按企业映射为独立租户迁移。
"""

from app.domain.legacy_migration.adapter import (
    LegacyMigrationAdapter,
    LegacyTableData,
    MigratedTableData,
)
from app.domain.legacy_migration.etl_tool import ETLMigrationTool, MigrationProgress
from app.domain.legacy_migration.verifier import MigrationVerifier, VerificationResult

__all__ = [
    "ETLMigrationTool",
    "LegacyMigrationAdapter",
    "LegacyTableData",
    "MigratedTableData",
    "MigrationProgress",
    "MigrationVerifier",
    "VerificationResult",
]