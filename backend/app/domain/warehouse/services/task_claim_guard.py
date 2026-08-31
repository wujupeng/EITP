"""Task 领取越权校验服务 - 校验领取人是否为分配人。"""

from __future__ import annotations

from uuid import UUID

from app.interfaces.middleware.error_handler import WMSError, WMSErrorCode


class TaskClaimGuard:
    """Task 领取越权校验领域服务。

    输入 task.assignee_id 与当前 user_id，输出是否允许领取。
    越权拒绝 EITP_WMS_TASK_ASSIGNMENT_DENIED 并记录越权审计。
    """

    @staticmethod
    def can_claim(assignee_id: UUID | None, user_id: UUID) -> bool:
        """校验当前用户是否可以领取任务。"""
        if assignee_id is None:
            return True
        return assignee_id == user_id

    @staticmethod
    def validate_claim(assignee_id: UUID | None, user_id: UUID, task_id: UUID) -> None:
        """校验领取权限，越权则抛出异常。"""
        if not TaskClaimGuard.can_claim(assignee_id, user_id):
            raise WMSError(
                WMSErrorCode.TASK_ASSIGNMENT_DENIED,
                "非分配人领取任务，越权拒绝",
                details={
                    "task_id": str(task_id),
                    "assignee_id": str(assignee_id) if assignee_id else None,
                    "claimer_id": str(user_id),
                },
            )