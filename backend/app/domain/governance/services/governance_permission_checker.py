"""治理权限校验器 - 集团级与企业级治理分离，禁止绕过治理工作流。

- 集团级治理由集团主数据管理员发起、集团审批人审批（spec 5.6.1.9）
- 企业级治理由企业主数据管理员发起、企业审批人审批
- 跨级审批被拒绝（EITP_MDM_CROSS_LEVEL_GOVERNANCE_DENIED，spec 5.6.3.4）
- 无审批权限用户审批被拒绝（EITP_MDM_GOVERNANCE_APPROVAL_DENIED，spec 5.6.3.3）
- 禁止绕过治理工作流直接修改发布数据（spec 5.6.1.10）
"""

from __future__ import annotations

from app.domain.governance.aggregates.governance_workflow_aggregate import (
    GovernanceLevel,
    GovernanceWorkflowAggregate,
)
from app.interfaces.middleware.error_handler import MDMError, MDMErrorCode
from app.interfaces.middleware.security_context import SecurityContext


class GovernancePermissionChecker:
    """治理权限校验器 - 集团级与企业级治理分离。"""

    GROUP_GOVERNANCE_PERMISSION = "mdm:governance:approve"
    ENTERPRISE_GOVERNANCE_PERMISSION = "mdm:governance:approve"
    GROUP_MANAGE_PERMISSION = "mdm:group_product:manage"
    ENTERPRISE_MANAGE_PERMISSION = "mdm:enterprise_product:manage"

    @classmethod
    def enforce_can_submit(
        cls,
        workflow: GovernanceWorkflowAggregate,
    ) -> None:
        """校验当前用户可提交该级别的治理申请。"""
        ctx = SecurityContext.current()
        if ctx is None:
            raise MDMError(
                MDMErrorCode.GOVERNANCE_APPROVAL_DENIED,
                "未认证，缺少安全上下文",
            )

        if workflow.is_group_level():
            if not ctx.is_authorized(cls.GROUP_MANAGE_PERMISSION):
                raise MDMError(
                    MDMErrorCode.CROSS_LEVEL_GOVERNANCE_DENIED,
                    "仅集团主数据管理员可提交集团级治理申请",
                )
        else:
            if not ctx.is_authorized(cls.ENTERPRISE_MANAGE_PERMISSION):
                raise MDMError(
                    MDMErrorCode.CROSS_LEVEL_GOVERNANCE_DENIED,
                    "仅企业主数据管理员可提交企业级治理申请",
                )

    @classmethod
    def enforce_can_approve(
        cls,
        workflow: GovernanceWorkflowAggregate,
    ) -> None:
        """校验当前用户可审批该级别的治理申请（spec 5.6.1.9）。"""
        ctx = SecurityContext.current()
        if ctx is None:
            raise MDMError(
                MDMErrorCode.GOVERNANCE_APPROVAL_DENIED,
                "未认证，缺少安全上下文",
            )

        if not ctx.is_authorized(cls.GROUP_GOVERNANCE_PERMISSION):
            raise MDMError(
                MDMErrorCode.GOVERNANCE_APPROVAL_DENIED,
                "无治理审批权限",
            )

        if workflow.is_group_level():
            if not ctx.user.is_platform_admin:
                raise MDMError(
                    MDMErrorCode.CROSS_LEVEL_GOVERNANCE_DENIED,
                    "企业审批人不可审批集团级变更申请",
                )

    @classmethod
    def enforce_no_bypass_governance(
        cls,
        entity_is_published: bool,
    ) -> None:
        """禁止绕过治理工作流直接修改发布数据（spec 5.6.1.10）。

        所有主数据变更必须通过治理工作流，直接修改已发布主数据被拒绝。
        """
        if entity_is_published:
            raise MDMError(
                MDMErrorCode.GOVERNANCE_REQUEST_NOT_EDITABLE,
                "已发布主数据不可直接修改，必须通过治理工作流",
            )