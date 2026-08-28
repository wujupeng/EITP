"""备份记录与保留策略 - 租户级独立备份。

spec 5.8 / design 2.3.2.7。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from uuid import UUID, uuid4


class BackupType(str, Enum):
    """备份类型。"""

    FULL = "full"
    INCREMENTAL = "incremental"


class BackupStatus(str, Enum):
    """备份状态。"""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    EXPIRED = "expired"


@dataclass
class BackupRecord:
    """备份记录 - 租户级独立备份。

    spec 5.8.1: 备份不影响其他租户。
    spec 5.8.1 规则 2: 恢复前校验备份完整性。
    """

    backup_id: UUID
    tenant_id: UUID
    backup_type: BackupType
    storage_uri: str
    checksum: str
    status: BackupStatus
    created_at: datetime
    expires_at: datetime
    size_bytes: int = 0
    failure_reason: str | None = None

    @classmethod
    def create(
        cls,
        tenant_id: UUID,
        backup_type: BackupType = BackupType.FULL,
        storage_uri: str = "",
        checksum: str = "",
        retain_days: int = 30,
    ) -> BackupRecord:
        now = datetime.now(timezone.utc)
        return cls(
            backup_id=uuid4(),
            tenant_id=tenant_id,
            backup_type=backup_type,
            storage_uri=storage_uri,
            checksum=checksum,
            status=BackupStatus.PENDING,
            created_at=now,
            expires_at=now + timedelta(days=retain_days),
        )

    def mark_completed(self, storage_uri: str, checksum: str, size_bytes: int) -> None:
        """标记备份完成。"""
        self.storage_uri = storage_uri
        self.checksum = checksum
        self.size_bytes = size_bytes
        self.status = BackupStatus.COMPLETED

    def mark_failed(self, reason: str) -> None:
        """标记备份失败。"""
        self.status = BackupStatus.FAILED
        self.failure_reason = reason

    def mark_expired(self) -> None:
        """标记备份过期。"""
        self.status = BackupStatus.EXPIRED

    def is_expired(self, now: datetime | None = None) -> bool:
        """是否已过期。"""
        now = now or datetime.now(timezone.utc)
        return now > self.expires_at

    def is_completed(self) -> bool:
        return self.status == BackupStatus.COMPLETED

    def verify_integrity(self, expected_checksum: str) -> bool:
        """校验备份完整性。

        spec 5.8.3 异常 1: 损坏返回 EITP_MT_BACKUP_CORRUPTED。
        """
        return self.checksum == expected_checksum and self.is_completed()


@dataclass(frozen=True)
class RetentionPolicy:
    """保留策略 - 超期备份自动清除。

    spec 5.8.1 规则 3: 保留策略可配置。
    """

    tenant_id: UUID
    retain_days: int = 30
    retain_copies: int = 10

    def should_expire(
        self,
        record: BackupRecord,
        now: datetime | None = None,
    ) -> bool:
        """判断备份是否应被清除。"""
        now = now or datetime.now(timezone.utc)
        if record.is_expired(now):
            return True
        return False

    def filter_expired(
        self,
        records: list[BackupRecord],
        now: datetime | None = None,
    ) -> list[BackupRecord]:
        """筛选超期备份。"""
        now = now or datetime.now(timezone.utc)
        return [r for r in records if self.should_expire(r, now)]

    def filter_redundant(
        self,
        records: list[BackupRecord],
    ) -> list[BackupRecord]:
        """筛选超出保留份数的冗余备份（按时间倒序保留最新 N 份）。"""
        completed = [r for r in records if r.is_completed()]
        completed.sort(key=lambda r: r.created_at, reverse=True)
        if len(completed) <= self.retain_copies:
            return []
        return completed[self.retain_copies:]