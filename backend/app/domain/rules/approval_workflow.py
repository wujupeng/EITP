"""审批流聚合根 - 按金额阈值路由到不同审批人，租户级独立配置。"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from uuid import UUID

from app.domain.shared.aggregate_root import AggregateRoot
from app.domain.shared.entity import EntityId
from app.interfaces.middleware.error_handler import DomainError, ErrorCode


class ApprovalAction(Enum):
    AUTO_APPROVE = "auto_approve"
    DEPT_MANAGER = "dept_manager"
    GENERAL_MANAGER = "general_manager"


@dataclass(frozen=True)
class ApprovalThreshold:
    """审批阈值 - 金额区间映射到审批动作。"""

    min_amount: float
    max_amount: float
    action: ApprovalAction
    approver_id: UUID | None = None

    def matches(self, amount: float) -> bool:
        return self.min_amount <= amount < self.max_amount


class ApprovalWorkflowAggregate(AggregateRoot):
    """审批流聚合根 - 租户级独立配置，按金额阈值路由。

    Rules:
    - 审批流不完整时单据挂起并通知租户管理员（EITP_MT_WORKFLOW_INCOMPLETE）
    - 跨租户引用审批流被拒绝
    """

    def __init__(self, id: EntityId, tenant_id: UUID, workflow_key: str) -> None:
        super().__init__(id)
        self._tenant_id = tenant_id
        self._workflow_key = workflow_key
        self._thresholds: list[ApprovalThreshold] = []

    @property
    def tenant_id(self) -> UUID:
        return self._tenant_id

    @property
    def workflow_key(self) -> str:
        return self._workflow_key

    def add_threshold(self, threshold: ApprovalThreshold) -> None:
        """添加审批阈值规则。"""
        self._thresholds.append(threshold)
        self._thresholds.sort(key=lambda t: t.min_amount)

    def route(self, amount: float) -> ApprovalAction:
        """按金额路由到审批动作。

        Raises:
            DomainError: 审批流不完整（无匹配阈值）
        """
        for threshold in self._thresholds:
            if threshold.matches(amount):
                return threshold.action

        raise DomainError(
            ErrorCode.WORKFLOW_INCOMPLETE,
            f"金额 {amount} 无匹配审批阈值，审批流不完整",
            details={"workflow_key": self._workflow_key, "amount": amount},
        )

    def is_complete(self) -> bool:
        """检查审批流是否完整（覆盖 0 到无穷大）。"""
        if not self._thresholds:
            return False
        if self._thresholds[0].min_amount > 0:
            return False
        for i in range(len(self._thresholds) - 1):
            if self._thresholds[i].max_amount != self._thresholds[i + 1].min_amount:
                return False
        if self._thresholds[-1].max_amount != float("inf"):
            return False
        return True