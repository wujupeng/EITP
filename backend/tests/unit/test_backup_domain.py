"""T10 租户备份与恢复单元测试。"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from app.domain.backup.backup_record import (
    BackupRecord,
    BackupStatus,
    BackupType,
    RetentionPolicy,
)
from app.domain.backup.restore_guard import RestoreGuard
from app.interfaces.middleware.error_handler import DomainError, ErrorCode


class TestBackupRecord:
    """T10-01: 备份记录。"""

    def test_create_backup(self) -> None:
        tenant = uuid4()
        record = BackupRecord.create(tenant)
        assert record.tenant_id == tenant
        assert record.status == BackupStatus.PENDING
        assert record.backup_type == BackupType.FULL

    def test_mark_completed(self) -> None:
        record = BackupRecord.create(uuid4())
        record.mark_completed("s3://bucket/backup.tar.gz", "sha256:abc", 1024)
        assert record.status == BackupStatus.COMPLETED
        assert record.checksum == "sha256:abc"
        assert record.size_bytes == 1024

    def test_mark_failed(self) -> None:
        record = BackupRecord.create(uuid4())
        record.mark_failed("存储空间不足")
        assert record.status == BackupStatus.FAILED
        assert record.failure_reason == "存储空间不足"

    def test_is_expired_false(self) -> None:
        record = BackupRecord.create(uuid4(), retain_days=30)
        assert record.is_expired() is False

    def test_is_expired_true(self) -> None:
        record = BackupRecord.create(uuid4(), retain_days=30)
        record.expires_at = datetime.now(timezone.utc) - timedelta(days=1)
        assert record.is_expired() is True

    def test_verify_integrity_success(self) -> None:
        record = BackupRecord.create(uuid4())
        record.mark_completed("uri", "sha256:abc", 100)
        assert record.verify_integrity("sha256:abc") is True

    def test_verify_integrity_checksum_mismatch(self) -> None:
        record = BackupRecord.create(uuid4())
        record.mark_completed("uri", "sha256:abc", 100)
        assert record.verify_integrity("sha256:xyz") is False

    def test_verify_integrity_not_completed(self) -> None:
        record = BackupRecord.create(uuid4())
        assert record.verify_integrity("") is False


class TestRetentionPolicy:
    """T10-01: 保留策略。"""

    def test_default_policy(self) -> None:
        policy = RetentionPolicy(tenant_id=uuid4())
        assert policy.retain_days == 30
        assert policy.retain_copies == 10

    def test_should_expire_expired(self) -> None:
        policy = RetentionPolicy(tenant_id=uuid4())
        record = BackupRecord.create(uuid4(), retain_days=1)
        record.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
        assert policy.should_expire(record) is True

    def test_should_expire_not_expired(self) -> None:
        policy = RetentionPolicy(tenant_id=uuid4())
        record = BackupRecord.create(uuid4(), retain_days=30)
        assert policy.should_expire(record) is False

    def test_filter_expired(self) -> None:
        policy = RetentionPolicy(tenant_id=uuid4())
        r1 = BackupRecord.create(uuid4(), retain_days=30)
        r2 = BackupRecord.create(uuid4(), retain_days=1)
        r2.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)

        expired = policy.filter_expired([r1, r2])
        assert len(expired) == 1
        assert expired[0] == r2

    def test_filter_redundant(self) -> None:
        policy = RetentionPolicy(tenant_id=uuid4(), retain_copies=2)
        records = []
        for i in range(5):
            r = BackupRecord.create(uuid4())
            r.mark_completed(f"uri{i}", f"checksum{i}", 100)
            r.created_at = datetime.now(timezone.utc) - timedelta(days=i)
            records.append(r)

        redundant = policy.filter_redundant(records)
        assert len(redundant) == 3

    def test_filter_redundant_within_limit(self) -> None:
        policy = RetentionPolicy(tenant_id=uuid4(), retain_copies=10)
        records = []
        for i in range(3):
            r = BackupRecord.create(uuid4())
            r.mark_completed(f"uri{i}", f"checksum{i}", 100)
            records.append(r)

        redundant = policy.filter_redundant(records)
        assert len(redundant) == 0


class TestRestoreGuard:
    """T10-04: 恢复守卫。"""

    def _make_completed_backup(self, tenant_id: UUID | None = None) -> BackupRecord:
        record = BackupRecord.create(tenant_id or uuid4())
        record.mark_completed("s3://bucket/backup.tar.gz", "sha256:abc", 1024)
        return record

    def test_enforce_same_tenant_allowed(self) -> None:
        tenant = uuid4()
        backup = self._make_completed_backup(tenant)
        RestoreGuard.enforce_same_tenant(backup, tenant)

    def test_enforce_same_tenant_denied(self) -> None:
        backup = self._make_completed_backup()
        with pytest.raises(DomainError) as exc:
            RestoreGuard.enforce_same_tenant(backup, uuid4())
        assert exc.value.code == ErrorCode.CROSS_TENANT_RESTORE_DENIED

    def test_enforce_integrity_success(self) -> None:
        backup = self._make_completed_backup()
        RestoreGuard.enforce_integrity(backup, "sha256:abc")

    def test_enforce_integrity_corrupted(self) -> None:
        backup = self._make_completed_backup()
        with pytest.raises(DomainError) as exc:
            RestoreGuard.enforce_integrity(backup, "sha256:xyz")
        assert exc.value.code == ErrorCode.BACKUP_CORRUPTED

    def test_enforce_completed_success(self) -> None:
        backup = self._make_completed_backup()
        RestoreGuard.enforce_completed(backup)

    def test_enforce_completed_pending_rejected(self) -> None:
        backup = BackupRecord.create(uuid4())
        with pytest.raises(DomainError) as exc:
            RestoreGuard.enforce_completed(backup)
        assert exc.value.code == ErrorCode.BACKUP_CORRUPTED