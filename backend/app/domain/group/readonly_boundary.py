"""ReadonlyBoundary - 集团只读边界守卫。

C-SEC-02: 集团管理员对子公司单据写操作一律拒绝，记录审计。
spec 5.6.1 规则 2/6：禁止集团管理员绕过只读边界直接改写子公司业务。
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from uuid import UUID

from structlog import get_logger

from app.domain.audit.audit_entry import AuditAction, AuditEntry
from app.domain.group.group_events import ReadonlyViolationEvent
from app.interfaces.middleware.error_handler import ErrorCode, GroupError

logger = get_logger(__name__)


class OperationType(str, Enum):
    """操作类型 - 区分读操作与写操作。"""

    READ = "read"
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    APPROVE = "approve"
    REJECT = "reject"

    @property
    def is_write(self) -> bool:
        return self != OperationType.READ


@dataclass(frozen=True)
class GroupActor:
    """集团管理员身份。"""

    actor_id: UUID
    enterprise_id: UUID
    is_group_admin: bool


class ReadonlyBoundary:
    """只读边界守卫 - 拦截集团管理员对子公司单据的写操作。

    职责：
    - enforce: 校验操作合法性，写操作拒绝并抛 GroupError
    - audit_violation: 记录越权审计日志
    """

    @staticmethod
    def enforce(
        actor: GroupActor,
        operation: OperationType,
        target_organization_id: UUID,
    ) -> None:
        """强制只读边界 - 集团管理员的写操作被拒绝。

        Raises:
            GroupError: EITP_MT_GROUP_READONLY_VIOLATION
        """
        if actor.is_group_admin and operation.is_write:
            ReadonlyBoundary.audit_violation(actor, operation, target_organization_id)
            raise GroupError(
                ErrorCode.GROUP_READONLY_VIOLATION,
                "集团权限为只读，不可修改子公司业务",
                details={
                    "actor_id": str(actor.actor_id),
                    "enterprise_id": str(actor.enterprise_id),
                    "operation": operation.value,
                    "target_organization_id": str(target_organization_id),
                },
            )

    @staticmethod
    def audit_violation(
        actor: GroupActor,
        operation: OperationType,
        target_organization_id: UUID,
    ) -> AuditEntry:
        """记录只读越权审计。"""
        logger.warning(
            "group_readonly_violation",
            actor_id=str(actor.actor_id),
            enterprise_id=str(actor.enterprise_id),
            operation=operation.value,
            target_organization_id=str(target_organization_id),
        )
        return AuditEntry.create(
            tenant_id=actor.enterprise_id,
            user_id=actor.actor_id,
            action=AuditAction.GROUP_READONLY_VIOLATION,
            entity_type="group_boundary",
            entity_id=str(target_organization_id),
            new_value={"operation": operation.value},
        )

    @staticmethod
    def build_violation_event(
        actor: GroupActor,
        operation: OperationType,
        target_organization_id: UUID,
    ) -> ReadonlyViolationEvent:
        """构建只读越权领域事件。"""
        return ReadonlyViolationEvent(
            enterprise_id=actor.enterprise_id,
            actor_id=actor.actor_id,
            operation=operation.value,
            target_organization_id=target_organization_id,
        )


class SubsidiaryIsolationGuard:
    """子公司管理员隔离守卫 - 仅返回其所属 Organization 数据。

    spec 5.6.1 规则 3：子公司管理员不可见兄弟公司数据。
    """

    @staticmethod
    def enforce(
        actor_org_id: UUID,
        requested_org_id: UUID,
        enterprise_id: UUID,
    ) -> None:
        """强制子公司隔离 - 请求非本公司数据时拒绝。

        Raises:
            GroupError: EITP_MT_SUBSIDIARY_ISOLATION_VIOLATION
        """
        if actor_org_id != requested_org_id:
            logger.warning(
                "subsidiary_isolation_violation",
                actor_org_id=str(actor_org_id),
                requested_org_id=str(requested_org_id),
                enterprise_id=str(enterprise_id),
            )
            raise GroupError(
                ErrorCode.SUBSIDIARY_ISOLATION_VIOLATION,
                "子公司管理员仅可访问本公司数据，不可见兄弟公司数据",
                details={
                    "actor_org_id": str(actor_org_id),
                    "requested_org_id": str(requested_org_id),
                    "enterprise_id": str(enterprise_id),
                },
            )

    @staticmethod
    def filter_visible(
        actor_org_id: UUID,
        all_org_ids: tuple[UUID, ...],
    ) -> tuple[UUID, ...]:
        """过滤可见的 Organization ID - 仅保留本公司。"""
        return tuple(oid for oid in all_org_ids if oid == actor_org_id)