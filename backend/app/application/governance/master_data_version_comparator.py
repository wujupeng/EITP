"""主数据版本对比器 - 对比任意两个版本的差异，支持版本回滚。

- 对比返回字段级差异（spec 5.6.1.7）
- 支持版本回滚到前一版本（spec 5.6.1.6）
- 回滚版本不存在时拒绝（EITP_MDM_VERSION_NOT_FOUND，spec 5.6.3.5）
"""

from __future__ import annotations

from app.domain.governance.aggregates.master_data_version_aggregate import (
    MasterDataVersionAggregate,
)
from app.interfaces.middleware.error_handler import MDMError, MDMErrorCode


class MasterDataVersionComparator:
    """主数据版本对比器。"""

    @staticmethod
    def compare(
        version_a: MasterDataVersionAggregate,
        version_b: MasterDataVersionAggregate,
    ) -> dict[str, dict]:
        """对比两个版本的差异，返回字段级差异（spec 5.6.1.7）。

        Returns:
            {field_name: {"before": value_a, "after": value_b}, ...}
            仅含差异字段。
        """
        snapshot_a = version_a.snapshot_after
        snapshot_b = version_b.snapshot_after

        all_keys = set(snapshot_a.keys()) | set(snapshot_b.keys())
        diff: dict[str, dict] = {}

        for key in all_keys:
            val_a = snapshot_a.get(key)
            val_b = snapshot_b.get(key)
            if val_a != val_b:
                diff[key] = {"before": val_a, "after": val_b}

        return diff

    @staticmethod
    def find_version(
        versions: list[MasterDataVersionAggregate],
        version_number: int,
    ) -> MasterDataVersionAggregate:
        """查找指定版本号，不存在时拒绝（spec 5.6.3.5）。"""
        for v in versions:
            if v.version_number == version_number:
                return v
        raise MDMError(
            MDMErrorCode.VERSION_NOT_FOUND,
            f"版本号 {version_number} 不存在",
        )

    @staticmethod
    def get_latest_version(
        versions: list[MasterDataVersionAggregate],
    ) -> MasterDataVersionAggregate | None:
        """获取最新版本。"""
        if not versions:
            return None
        return max(versions, key=lambda v: v.version_number)

    @staticmethod
    def get_previous_version(
        versions: list[MasterDataVersionAggregate],
        current_version_number: int,
    ) -> MasterDataVersionAggregate:
        """获取前一版本用于回滚（spec 5.6.1.6）。

        回滚版本不存在时拒绝（spec 5.6.3.5）。
        """
        if current_version_number <= 1:
            raise MDMError(
                MDMErrorCode.VERSION_NOT_FOUND,
                f"版本号 {current_version_number} 无前一版本可回滚",
            )
        return MasterDataVersionComparator.find_version(
            versions, current_version_number - 1
        )

    @staticmethod
    def rollback_to(
        versions: list[MasterDataVersionAggregate],
        target_version_number: int,
    ) -> MasterDataVersionAggregate:
        """回滚到指定版本（spec 5.6.1.6）。

        回滚版本不存在时拒绝（spec 5.6.3.5）。
        """
        return MasterDataVersionComparator.find_version(
            versions, target_version_number
        )