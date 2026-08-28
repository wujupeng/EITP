"""T11 存量 PHP 数据迁移单元测试。"""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.domain.legacy_migration.adapter import (
    DefaultMigrationAdapter,
    LegacyMigrationAdapter,
    LegacyTableData,
    MigratedTableData,
)
from app.domain.legacy_migration.etl_tool import (
    ETLMigrationTool,
    EnterpriseMigrationRecord,
    MigrationProgress,
    MigrationStatus,
)
from app.domain.legacy_migration.verifier import (
    MigrationVerifier,
    VerificationResult,
    VerificationStatus,
)


class TestLegacyMigrationAdapter:
    """T11-01: 迁移适配器契约。"""

    def test_adapt_injects_tenant_id(self) -> None:
        adapter = DefaultMigrationAdapter()
        tenant_id = uuid4()
        legacy = LegacyTableData(
            table_name="orders",
            enterprise_key="ent_a",
            rows=[{"id": 1, "amount": 100}, {"id": 2, "amount": 200}],
        )
        result = adapter.adapt(legacy, {"ent_a": tenant_id})
        assert result.tenant_id == tenant_id
        assert all("tenant_id" in row for row in result.rows)
        assert all(row["tenant_id"] == str(tenant_id) for row in result.rows)

    def test_adapt_unknown_enterprise_raises(self) -> None:
        adapter = DefaultMigrationAdapter()
        legacy = LegacyTableData(table_name="orders", enterprise_key="unknown")
        with pytest.raises(ValueError, match="未找到"):
            adapter.adapt(legacy, {})

    def test_adapt_preserves_data(self) -> None:
        adapter = DefaultMigrationAdapter()
        tenant_id = uuid4()
        legacy = LegacyTableData(
            table_name="products",
            enterprise_key="ent_a",
            rows=[{"id": 1, "name": "商品A", "price": 50}],
        )
        result = adapter.adapt(legacy, {"ent_a": tenant_id})
        assert result.rows[0]["id"] == 1
        assert result.rows[0]["name"] == "商品A"
        assert result.rows[0]["price"] == 50

    def test_adapt_is_abstract(self) -> None:
        assert LegacyMigrationAdapter.__abstractmethods__


class TestETLMigrationTool:
    """T11-02: ETL 迁移工具。"""

    def test_provision_tenant(self) -> None:
        tool = ETLMigrationTool()
        tenant_id = tool.provision_tenant_for_enterprise("ent_a")
        assert tenant_id is not None
        same_id = tool.provision_tenant_for_enterprise("ent_a")
        assert same_id == tenant_id

    def test_migrate_table(self) -> None:
        tool = ETLMigrationTool()
        tool.provision_tenant_for_enterprise("ent_a")
        legacy = LegacyTableData(
            table_name="orders",
            enterprise_key="ent_a",
            rows=[{"id": 1}],
        )
        result = tool.migrate_table(legacy)
        assert result.table_name == "orders"
        assert "tenant_id" in result.rows[0]

    def test_migrate_batch(self) -> None:
        tool = ETLMigrationTool()
        batch = [
            LegacyTableData("orders", "ent_a", [{"id": 1}, {"id": 2}]),
            LegacyTableData("orders", "ent_b", [{"id": 3}]),
            LegacyTableData("products", "ent_a", [{"id": 1}]),
        ]
        progress = tool.migrate_batch(batch)
        assert progress.total_enterprises == 2
        assert progress.migrated_enterprises == 2
        assert progress.failed_enterprises == 0
        assert progress.is_complete is True

    def test_migrate_batch_with_failure(self) -> None:
        tool = ETLMigrationTool()
        batch = [
            LegacyTableData("orders", "ent_a", [{"id": 1}]),
            LegacyTableData("orders", "unknown_ent", [{"id": 2}]),
        ]
        progress = tool.migrate_batch(batch)
        assert progress.failed_enterprises >= 0


class TestMigrationProgress:
    """T11-04: 迁移进度追踪。"""

    def test_success_rate(self) -> None:
        progress = MigrationProgress(task_id=uuid4(), total_enterprises=4)
        progress.add_record(EnterpriseMigrationRecord("a", uuid4(), MigrationStatus.COMPLETED))
        progress.add_record(EnterpriseMigrationRecord("b", uuid4(), MigrationStatus.COMPLETED))
        progress.add_record(EnterpriseMigrationRecord("c", uuid4(), MigrationStatus.FAILED))
        assert progress.migrated_enterprises == 2
        assert progress.failed_enterprises == 1
        assert progress.success_rate == 0.5

    def test_is_complete(self) -> None:
        progress = MigrationProgress(task_id=uuid4(), total_enterprises=2)
        assert progress.is_complete is False
        progress.add_record(EnterpriseMigrationRecord("a", uuid4(), MigrationStatus.COMPLETED))
        progress.add_record(EnterpriseMigrationRecord("b", uuid4(), MigrationStatus.FAILED))
        assert progress.is_complete is True


class TestMigrationVerifier:
    """T11-03: 迁移校验与回滚。"""

    def test_compute_hash_consistent(self) -> None:
        rows = [{"id": 1, "name": "A"}, {"id": 2, "name": "B"}]
        h1 = MigrationVerifier.compute_hash(rows)
        h2 = MigrationVerifier.compute_hash(rows)
        assert h1 == h2

    def test_compute_hash_order_independent(self) -> None:
        rows1 = [{"id": 1}, {"id": 2}]
        rows2 = [{"id": 2}, {"id": 1}]
        assert MigrationVerifier.compute_hash(rows1) == MigrationVerifier.compute_hash(rows2)

    def test_compute_hash_different_data(self) -> None:
        rows1 = [{"id": 1}]
        rows2 = [{"id": 2}]
        assert MigrationVerifier.compute_hash(rows1) != MigrationVerifier.compute_hash(rows2)

    def test_verify_table_passed(self) -> None:
        tenant = uuid4()
        legacy = LegacyTableData("orders", "ent_a", [{"id": 1, "amount": 100}])
        migrated = MigratedTableData("orders", tenant, [{"id": 1, "amount": 100, "tenant_id": str(tenant)}])
        result = MigrationVerifier.verify_table(legacy, migrated)
        assert result.status == VerificationStatus.PASSED
        assert result.row_count_match is True

    def test_verify_table_row_count_mismatch(self) -> None:
        tenant = uuid4()
        legacy = LegacyTableData("orders", "ent_a", [{"id": 1}, {"id": 2}])
        migrated = MigratedTableData("orders", tenant, [{"id": 1, "tenant_id": str(tenant)}])
        result = MigrationVerifier.verify_table(legacy, migrated)
        assert result.status == VerificationStatus.FAILED
        assert result.row_count_match is False

    def test_verify_table_hash_mismatch(self) -> None:
        tenant = uuid4()
        legacy = LegacyTableData("orders", "ent_a", [{"id": 1, "amount": 100}])
        migrated = MigratedTableData("orders", tenant, [{"id": 1, "amount": 200, "tenant_id": str(tenant)}])
        result = MigrationVerifier.verify_table(legacy, migrated)
        assert result.status == VerificationStatus.FAILED

    def test_verify_batch_all_passed(self) -> None:
        tenant = uuid4()
        task_id = uuid4()
        legacy_batch = [
            LegacyTableData("orders", "ent_a", [{"id": 1}]),
            LegacyTableData("products", "ent_a", [{"id": 1}]),
        ]
        migrated_batch = [
            MigratedTableData("orders", tenant, [{"id": 1, "tenant_id": str(tenant)}]),
            MigratedTableData("products", tenant, [{"id": 1, "tenant_id": str(tenant)}]),
        ]
        result = MigrationVerifier.verify_batch(task_id, legacy_batch, migrated_batch)
        assert result.all_passed is True
        assert result.passed_count == 2
        assert result.failed_count == 0

    def test_verify_batch_with_failure(self) -> None:
        tenant = uuid4()
        task_id = uuid4()
        legacy_batch = [
            LegacyTableData("orders", "ent_a", [{"id": 1}]),
            LegacyTableData("products", "ent_a", [{"id": 1}, {"id": 2}]),
        ]
        migrated_batch = [
            MigratedTableData("orders", tenant, [{"id": 1, "tenant_id": str(tenant)}]),
            MigratedTableData("products", tenant, [{"id": 1, "tenant_id": str(tenant)}]),
        ]
        result = MigrationVerifier.verify_batch(task_id, legacy_batch, migrated_batch)
        assert result.all_passed is False
        assert result.failed_count == 1

    def test_verify_with_key_fields(self) -> None:
        tenant = uuid4()
        legacy = LegacyTableData("orders", "ent_a", [{"id": 1, "amount": 100, "note": "A"}])
        migrated = MigratedTableData("orders", tenant, [{"id": 1, "amount": 100, "note": "B", "tenant_id": str(tenant)}])
        result = MigrationVerifier.verify_table(legacy, migrated, key_fields=["id", "amount"])
        assert result.status == VerificationStatus.PASSED