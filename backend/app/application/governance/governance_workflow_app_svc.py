"""治理工作流应用服务 - 编排变更申请创建/提交/审批/发布/回滚/查询命令。"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.application.governance.governance_workflow_executor import (
    GovernanceWorkflowExecutor,
)
from app.domain.governance.aggregates.governance_workflow_aggregate import (
    GovernanceLevel,
    GovernanceWorkflowAggregate,
)
from app.domain.governance.services.governance_permission_checker import (
    GovernancePermissionChecker,
)
from app.domain.governance.value_objects.governance_state import GovernanceState
from app.domain.shared.entity import EntityId
from app.infrastructure.governance.governance_repositories import (
    GovernanceWorkflowRepository,
)
from app.interfaces.middleware.error_handler import MDMError, MDMErrorCode


class GovernanceWorkflowAppSvc:
    """治理工作流应用服务。"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = GovernanceWorkflowRepository()

    async def create_request(
        self,
        governance_level: GovernanceLevel,
        entity_type: str,
        target_version_id: UUID,
        tenant_id: UUID | None = None,
        entity_id: UUID | None = None,
    ) -> GovernanceWorkflowAggregate:
        wf = GovernanceWorkflowExecutor.create_request(
            governance_level=governance_level,
            entity_type=entity_type,
            target_version_id=target_version_id,
            tenant_id=tenant_id,
            entity_id=entity_id,
        )
        await self._repo.save(self._session, wf)
        return wf

    async def submit_request(self, request_id: UUID, submitted_by: UUID) -> GovernanceWorkflowAggregate:
        orm = await self._repo.get_by_id(self._session, request_id)
        if orm is None:
            raise MDMError(MDMErrorCode.VERSION_NOT_FOUND, f"治理申请 {request_id} 不存在")
        agg = self._orm_to_agg(orm)
        GovernancePermissionChecker.enforce_can_submit(agg)
        GovernanceWorkflowExecutor.submit_request(agg, submitted_by)
        await self._repo.update(self._session, agg)
        return agg

    async def approve_request(self, request_id: UUID, approver: UUID, opinion: str) -> GovernanceWorkflowAggregate:
        orm = await self._repo.get_by_id(self._session, request_id)
        if orm is None:
            raise MDMError(MDMErrorCode.VERSION_NOT_FOUND, f"治理申请 {request_id} 不存在")
        agg = self._orm_to_agg(orm)
        GovernancePermissionChecker.enforce_can_approve(agg)
        GovernanceWorkflowExecutor.approve_request(agg, approver, opinion)
        await self._repo.update(self._session, agg)
        return agg

    async def reject_request(self, request_id: UUID, rejecter: UUID, opinion: str) -> GovernanceWorkflowAggregate:
        orm = await self._repo.get_by_id(self._session, request_id)
        if orm is None:
            raise MDMError(MDMErrorCode.VERSION_NOT_FOUND, f"治理申请 {request_id} 不存在")
        agg = self._orm_to_agg(orm)
        GovernanceWorkflowExecutor.reject_request(agg, rejecter, opinion)
        await self._repo.update(self._session, agg)
        return agg

    async def publish_request(self, request_id: UUID, published_by: UUID) -> GovernanceWorkflowAggregate:
        orm = await self._repo.get_by_id(self._session, request_id)
        if orm is None:
            raise MDMError(MDMErrorCode.VERSION_NOT_FOUND, f"治理申请 {request_id} 不存在")
        agg = self._orm_to_agg(orm)
        GovernanceWorkflowExecutor.publish_request(agg, published_by)
        await self._repo.update(self._session, agg)
        return agg

    async def rollback_request(self, request_id: UUID, rollback_by: UUID, reason: str) -> GovernanceWorkflowAggregate:
        orm = await self._repo.get_by_id(self._session, request_id)
        if orm is None:
            raise MDMError(MDMErrorCode.VERSION_NOT_FOUND, f"治理申请 {request_id} 不存在")
        agg = self._orm_to_agg(orm)
        GovernanceWorkflowExecutor.rollback_request(agg, rollback_by, reason)
        await self._repo.update(self._session, agg)
        return agg

    async def list_by_tenant(self, tenant_id: UUID, offset: int = 0, limit: int = 50):
        return await self._repo.list_by_tenant(self._session, tenant_id, offset, limit)

    async def list_pending(self, offset: int = 0, limit: int = 50):
        return await self._repo.list_pending(self._session, offset, limit)

    def _orm_to_agg(self, orm) -> GovernanceWorkflowAggregate:
        return GovernanceWorkflowAggregate(
            id=EntityId(orm.request_id),
            governance_level=GovernanceLevel(orm.governance_level),
            entity_type=orm.entity_type,
            target_version_id=orm.target_version_id,
            tenant_id=orm.tenant_id,
            entity_id=orm.entity_id,
            status=GovernanceState(orm.status),
            submitted_by=orm.submitted_by,
            submitted_at=orm.submitted_at,
            approved_by=orm.approved_by,
            approved_at=orm.approved_at,
            approval_opinion=orm.approval_opinion,
            published_by=orm.published_by,
            published_at=orm.published_at,
            rollback_by=orm.rollback_by,
            rollback_at=orm.rollback_at,
            rollback_reason=orm.rollback_reason,
        )
