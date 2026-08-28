"""恢复守卫 - 跨租户恢复拒绝与完整性校验。

C-BACKUP-01 / spec 5.8.3 异常 2。
"""

from __future__ import annotations

from uuid import UUID

from structlog import get_logger

from app.domain.backup.backup_record import BackupRecord
from app.interfaces.middleware.error_handler import ErrorCode, GroupError

logger = get_logger(__name__)


class RestoreGuard:
    """恢复守卫 - 跨租户恢复拒绝与完整性校验。

    spec 5.8.1 规则 2: 恢复前校验备份完整性。
    spec 5.8.3 异常 2: 跨租户恢复拒绝（C-BACKUP-01）。
    """

    @staticmethod
    def enforce_same_tenant(
        backup: BackupRecord,
        target_tenant_id: UUID,
    ) -> None:
        """强制恢复目标与备份源租户一致。

        Raises:
            GroupError: EITP_MT_CROSS_TENANT_RESTORE_DENIED
        """
        if backup.tenant_id != target_tenant_id:
            logger.warning(
                "cross_tenant_restore_denied",
                backup_tenant=str(backup.tenant_id),
                target_tenant=str(target_tenant_id),
            )
            raise GroupError(
                ErrorCode.CROSS_TENANT_RESTORE_DENIED,
                "跨租户恢复被拒绝，恢复目标必须与备份源租户一致",
                details={
                    "backup_tenant_id": str(backup.tenant_id),
                    "target_tenant_id": str(target_tenant_id),
                },
            )

    @staticmethod
    def enforce_integrity(
        backup: BackupRecord,
        expected_checksum: str,
    ) -> None:
        """强制备份完整性校验。

        Raises:
            GroupError: EITP_MT_BACKUP_CORRUPTED
        """
        if not backup.verify_integrity(expected_checksum):
            logger.warning(
                "backup_corrupted",
                backup_id=str(backup.backup_id),
                expected=expected_checksum,
                actual=backup.checksum,
            )
            raise GroupError(
                ErrorCode.BACKUP_CORRUPTED,
                "备份完整性校验失败，备份可能已损坏",
                details={
                    "backup_id": str(backup.backup_id),
                    "expected_checksum": expected_checksum,
                    "actual_checksum": backup.checksum,
                },
            )

    @staticmethod
    def enforce_completed(backup: BackupRecord) -> None:
        """强制备份状态为已完成。

        Raises:
            GroupError: EITP_MT_BACKUP_CORRUPTED
        """
        if not backup.is_completed():
            raise GroupError(
                ErrorCode.BACKUP_CORRUPTED,
                f"备份状态为 {backup.status.value}，不可恢复",
                details={"backup_id": str(backup.backup_id)},
            )