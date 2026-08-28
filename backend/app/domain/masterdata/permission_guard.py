"""主数据权限边界守卫 - 子公司反向修改集团基准被拒绝。

C-MASTER-01 / spec 5.9.1 规则 5。
"""

from __future__ import annotations

from uuid import UUID

from structlog import get_logger

from app.interfaces.middleware.error_handler import ErrorCode, GroupError

logger = get_logger(__name__)


class MasterDataPermissionGuard:
    """主数据权限边界守卫。

    Rules:
    - 集团基准仅集团管理员可写（EITP_MT_MASTER_BASE_READONLY）
    - 公司级属性仅子公司管理员可写
    - 仓库级属性仅仓库归属公司管理员可写
    """

    @staticmethod
    def enforce_base_write(
        is_group_admin: bool,
        enterprise_id: UUID,
        master_data_id: UUID,
    ) -> None:
        """校验集团基准写权限 - 子公司管理员被拒绝。

        Raises:
            GroupError: EITP_MT_MASTER_BASE_READONLY
        """
        if not is_group_admin:
            logger.warning(
                "master_base_readonly_violation",
                enterprise_id=str(enterprise_id),
                master_data_id=str(master_data_id),
            )
            raise GroupError(
                ErrorCode.MASTER_BASE_READONLY,
                "集团主数据基准仅集团管理员可修改",
                details={
                    "enterprise_id": str(enterprise_id),
                    "master_data_id": str(master_data_id),
                },
            )

    @staticmethod
    def enforce_company_override_write(
        actor_org_id: UUID,
        target_org_id: UUID,
    ) -> None:
        """校验公司级属性写权限 - 仅本公司管理员可写。

        Raises:
            GroupError: EITP_MT_MASTER_ATTR_CONFLICT
        """
        if actor_org_id != target_org_id:
            raise GroupError(
                ErrorCode.MASTER_ATTR_CONFLICT,
                "公司级属性仅本公司管理员可维护",
                details={
                    "actor_org_id": str(actor_org_id),
                    "target_org_id": str(target_org_id),
                },
            )

    @staticmethod
    def check_attr_conflict(
        base_attrs: dict,
        override_attrs: dict,
        constrained_keys: set[str] | None = None,
    ) -> None:
        """检查公司级属性与集团基准约束冲突。

        Args:
            constrained_keys: 受基准约束的属性键集合，这些键不允许在公司级覆盖

        Raises:
            GroupError: EITP_MT_MASTER_ATTR_CONFLICT
        """
        if constrained_keys is None:
            return

        conflicting = set(override_attrs.keys()) & constrained_keys
        if conflicting:
            raise GroupError(
                ErrorCode.MASTER_ATTR_CONFLICT,
                f"公司级属性 {conflicting} 与集团基准约束冲突",
                details={
                    "conflicting_keys": list(conflicting),
                    "constrained_keys": list(constrained_keys),
                },
            )