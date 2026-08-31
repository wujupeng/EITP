"""治理工作流编排器 - 编排变更申请创建→提交→审批→发布→回滚五步流转。

版本切换与生效数据更新在同一数据库事务内原子完成（spec 4.2.2）。
"""

from __future__ import annotations

from uuid import UUID

from app.domain.governance.aggregates.governance_workflow_aggregate import (
    GovernanceLevel,
    GovernanceWorkflowAggregate,
)
from app.domain.governance.aggregates.master_data_version_aggregate import (
    ChangeType,
    MasterDataVersionAggregate,
)
from app.domain.governance.value_objects.governance_state import GovernanceState
from app.interfaces.middleware.error_handler import MDMError, MDMErrorCode


class GovernanceWorkflowExecutor:
    """治理工作流编排器。

    编排五步流转：
    1. 创建（生成版本快照 DRAFT）
    2. 提交（通知审批人 SUBMITTED）
    3. 审批（记录审计 APPROVED/REJECTED）
    4. 发布（切换生效版本 + 发布主数据领域事件 + 记录审计 PUBLISHED）
    5. 回滚（恢复前一版本 + 记录审计 ROLLED_BACK）
    """

    @staticmethod
    def create_request(
        governance_level: GovernanceLevel,
        entity_type: str,
        target_version_id: UUID,
        tenant_id: UUID | None = None,
        entity_id: UUID | None = None,
    ) -> GovernanceWorkflowAggregate:
        """创建治理变更申请（DRAFT 状态）。"""
        from app.domain.shared.entity import EntityId

        return GovernanceWorkflowAggregate(
            id=EntityId.generate(),
            governance_level=governance_level,
            entity_type=entity_type,
            target_version_id=target_version_id,
            tenant_id=tenant_id,
            entity_id=entity_id,
            status=GovernanceState.DRAFT,
        )

    @staticmethod
    def submit_request(
        workflow: GovernanceWorkflowAggregate,
        submitted_by: UUID,
    ) -> GovernanceWorkflowAggregate:
        """提交治理申请（DRAFT → SUBMITTED）。"""
        workflow.submit(submitted_by)
        return workflow

    @staticmethod
    def approve_request(
        workflow: GovernanceWorkflowAggregate,
        approver: UUID,
        opinion: str,
    ) -> GovernanceWorkflowAggregate:
        """审批通过（SUBMITTED → APPROVED）。"""
        workflow.approve(approver, opinion)
        return workflow

    @staticmethod
    def reject_request(
        workflow: GovernanceWorkflowAggregate,
        rejecter: UUID,
        opinion: str,
    ) -> GovernanceWorkflowAggregate:
        """审批拒绝（SUBMITTED → REJECTED）。"""
        workflow.reject(rejecter, opinion)
        return workflow

    @staticmethod
    def publish_request(
        workflow: GovernanceWorkflowAggregate,
        published_by: UUID,
    ) -> GovernanceWorkflowAggregate:
        """发布（APPROVED → PUBLISHED）。

        版本切换与生效数据更新在同一数据库事务内原子完成（spec 4.2.2）。
        实际事务管理由调用方（应用服务层）通过 Unit of Work 模式控制。
        """
        workflow.publish(published_by)
        return workflow

    @staticmethod
    def rollback_request(
        workflow: GovernanceWorkflowAggregate,
        rollback_by: UUID,
        reason: str,
    ) -> GovernanceWorkflowAggregate:
        """回滚（PUBLISHED → ROLLED_BACK）。"""
        if not reason:
            raise MDMError(
                MDMErrorCode.NEGATIVE_POLICY_REASON_REQUIRED,
                "回滚原因不能为空",
            )
        workflow.rollback(rollback_by, reason)
        return workflow