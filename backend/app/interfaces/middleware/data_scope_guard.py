"""DataScopeGuard - 应用层 DataScope 收敛与越权审计。

C-SEC-03: 禁止前端隐藏式隔离，必须在应用层强制收敛。
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from uuid import UUID

from structlog import get_logger

from app.interfaces.middleware.tenant_context import TenantContext

logger = get_logger(__name__)


class DataScopeLevel(Enum):
    """数据范围级别 - 从宽到窄。"""

    PLATFORM = "platform"
    ENTERPRISE = "enterprise"
    ORGANIZATION = "organization"
    SITE = "site"
    WAREHOUSE = "warehouse"
    SELF = "self"


@dataclass(frozen=True)
class DataScope:
    """数据范围 - 用户授权的可见数据范围。"""

    tenant_id: UUID
    level: DataScopeLevel
    scope_ids: tuple[UUID, ...]

    def contains(self, other_tenant_id: UUID) -> bool:
        """检查目标租户是否在授权范围内。"""
        return self.tenant_id == other_tenant_id

    def is_subscope_of(self, requested_ids: tuple[UUID, ...]) -> bool:
        """检查请求范围是否是授权范围的子集。"""
        return all(rid in self.scope_ids for rid in requested_ids)


class DataScopeGuard:
    """DataScope 守卫 - 强制收敛用户请求范围到授权子集。

    越权尝试记录审计并通知租户管理员。
    """

    @staticmethod
    def resolve_scope(ctx: TenantContext) -> DataScope:
        """从租户上下文解析授权 DataScope。"""
        if ctx.is_platform_admin:
            return DataScope(
                tenant_id=ctx.tenant_id,
                level=DataScopeLevel.PLATFORM,
                scope_ids=(),
            )
        return DataScope(
            tenant_id=ctx.tenant_id,
            level=DataScopeLevel.ENTERPRISE,
            scope_ids=(),
        )

    @staticmethod
    def enforce_tenant_isolation(
        ctx: TenantContext,
        target_tenant_id: UUID,
    ) -> None:
        """强制租户隔离 - 拒绝跨租户访问。

        Raises:
            DomainError: 跨租户引用被拒绝
        """
        if not ctx.is_platform_admin and ctx.tenant_id != target_tenant_id:
            logger.warning(
                "cross_tenant_access_denied",
                user_tenant=str(ctx.tenant_id),
                target_tenant=str(target_tenant_id),
                user_id=str(ctx.user_id) if ctx.user_id else None,
            )
            from app.interfaces.middleware.error_handler import (
                DomainError,
                ErrorCode,
            )
            raise DomainError(
                ErrorCode.CROSS_TENANT_REF_DENIED,
                "跨租户引用被拒绝",
                details={
                    "user_tenant": str(ctx.tenant_id),
                    "target_tenant": str(target_tenant_id),
                },
            )

    @staticmethod
    def enforce_scope_subset(
        authorized: DataScope,
        requested_ids: tuple[UUID, ...],
    ) -> tuple[UUID, ...]:
        """收敛请求范围到授权子集。

        Returns:
            收敛后的有效范围 ID 元组

        若请求范围超出授权范围，记录审计并返回授权范围的交集。
        """
        if not requested_ids:
            return authorized.scope_ids

        if authorized.is_subscope_of(requested_ids):
            return requested_ids

        valid_ids = tuple(rid for rid in requested_ids if rid in authorized.scope_ids)
        rejected_ids = tuple(rid for rid in requested_ids if rid not in authorized.scope_ids)

        if rejected_ids:
            logger.warning(
                "datascope_violation",
                authorized_level=authorized.level.value,
                rejected_count=len(rejected_ids),
                rejected_ids=[str(rid) for rid in rejected_ids],
            )

        return valid_ids