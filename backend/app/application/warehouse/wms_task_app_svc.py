"""WMS Task 应用服务 - 编排 Task 创建/分配/领取/取消/查询。

序列：权限→状态机校验→越权校验→状态流转→审计→事件。
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.warehouse.services.task_claim_guard import TaskClaimGuard
from app.infrastructure.warehouse.models import WmsOperationAuditORM, WmsTaskORM
from app.infrastructure.warehouse.wms_task_repository import WmsTaskRepository
from app.interfaces.middleware.error_handler import WMSError, WMSErrorCode
from app.interfaces.middleware.security_context import SecurityContext


class WmsTaskAppSvc:
    """WMS Task 应用服务。"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._task_repo = WmsTaskRepository()
        self._claim_guard = TaskClaimGuard()

    def _check_auth(self, tenant_id: UUID, permission: str) -> None:
        ctx = SecurityContext.current()
        if ctx is None:
            raise WMSError(WMSErrorCode.SERVICE_UNAVAILABLE, "未认证")
        if ctx.tenant.tenant_id != tenant_id:
            raise WMSError(WMSErrorCode.CROSS_TENANT_REF_DENIED, "跨租户操作被拒绝")

    async def create_task(
        self,
        tenant_id: UUID,
        task_type: str,
        document_id: UUID,
        document_type: str,
        priority: str = "medium",
        idempotency_key: str | None = None,
        correlation_id: str | None = None,
    ) -> WmsTaskORM:
        """创建 Task。"""
        self._check_auth(tenant_id, "wms:task:manage")

        if idempotency_key is not None:
            existing = await self._task_repo.get_by_idempotency_key(
                self._session, tenant_id, idempotency_key
            )
            if existing is not None:
                return existing

        orm = WmsTaskORM(
            tenant_id=tenant_id,
            task_type=task_type,
            document_id=document_id,
            document_type=document_type,
            priority=priority,
            idempotency_key=idempotency_key,
            correlation_id=correlation_id,
            status="created",
        )
        return await self._task_repo.save(self._session, orm)

    async def assign_task(
        self,
        tenant_id: UUID,
        task_id: UUID,
        assignee_id: UUID,
        operated_by: UUID,
    ) -> dict:
        """分配 Task。"""
        self._check_auth(tenant_id, "wms:task:assign")

        task = await self._task_repo.get_by_id(self._session, tenant_id, task_id)
        if task is None:
            raise WMSError(WMSErrorCode.WAREHOUSE_NOT_FOUND, f"Task {task_id} 不存在")
        if task.status != "created":
            raise WMSError(WMSErrorCode.TASK_INVALID_STATE_TRANSITION, "Task 状态不允许分配")

        await self._task_repo.update_status(
            self._session, tenant_id, task_id, "assigned", assigned_at=datetime.now(timezone.utc)
        )
        task.assignee_id = assignee_id
        await self._session.flush()

        audit = WmsOperationAuditORM(
            tenant_id=tenant_id,
            user_id=operated_by,
            event_type="wms_task_assigned",
            task_id=task_id,
            before_state={"status": "created"},
            after_state={"status": "assigned", "assignee_id": str(assignee_id)},
            reason=f"Task {task_id} 分配给 {assignee_id}",
        )
        self._session.add(audit)
        await self._session.flush()

        return {"task_id": str(task_id), "status": "assigned", "assignee_id": str(assignee_id)}

    async def claim_task(
        self,
        tenant_id: UUID,
        task_id: UUID,
        user_id: UUID,
    ) -> dict:
        """领取 Task。"""
        self._check_auth(tenant_id, "wms:task:claim")

        task = await self._task_repo.get_by_id(self._session, tenant_id, task_id)
        if task is None:
            raise WMSError(WMSErrorCode.WAREHOUSE_NOT_FOUND, f"Task {task_id} 不存在")
        if task.status != "assigned":
            raise WMSError(WMSErrorCode.TASK_INVALID_STATE_TRANSITION, "Task 状态不允许领取")
        if task.assignee_id != user_id:
            raise WMSError(WMSErrorCode.TASK_ASSIGNMENT_DENIED, "越权领取被拒绝")

        await self._task_repo.update_status(
            self._session, tenant_id, task_id, "in_progress", started_at=datetime.now(timezone.utc)
        )

        audit = WmsOperationAuditORM(
            tenant_id=tenant_id,
            user_id=user_id,
            event_type="wms_task_claimed",
            task_id=task_id,
            before_state={"status": "assigned"},
            after_state={"status": "in_progress"},
            reason=f"Task {task_id} 被 {user_id} 领取",
        )
        self._session.add(audit)
        await self._session.flush()

        return {"task_id": str(task_id), "status": "in_progress"}

    async def cancel_task(
        self,
        tenant_id: UUID,
        task_id: UUID,
        operated_by: UUID,
        reason: str = "",
    ) -> dict:
        """取消 Task。"""
        self._check_auth(tenant_id, "wms:task:cancel")

        task = await self._task_repo.get_by_id(self._session, tenant_id, task_id)
        if task is None:
            raise WMSError(WMSErrorCode.WAREHOUSE_NOT_FOUND, f"Task {task_id} 不存在")
        if task.status in ("completed", "cancelled"):
            raise WMSError(WMSErrorCode.TASK_INVALID_STATE_TRANSITION, "Task 状态不允许取消")

        await self._task_repo.update_status(
            self._session, tenant_id, task_id, "cancelled"
        )

        audit = WmsOperationAuditORM(
            tenant_id=tenant_id,
            user_id=operated_by,
            event_type="wms_task_cancelled",
            task_id=task_id,
            before_state={"status": task.status},
            after_state={"status": "cancelled"},
            reason=reason or f"Task {task_id} 取消",
        )
        self._session.add(audit)
        await self._session.flush()

        return {"task_id": str(task_id), "status": "cancelled"}

    async def query_tasks_by_status(
        self, tenant_id: UUID, status: str, offset: int = 0, limit: int = 50
    ) -> list[dict]:
        """按状态查询 Task。"""
        self._check_auth(tenant_id, "wms:task:query")
        tasks = await self._task_repo.list_by_status(
            self._session, tenant_id, status, offset, limit
        )
        return [self._to_dict(t) for t in tasks]

    async def query_tasks_by_assignee(
        self, tenant_id: UUID, assignee_id: UUID, status: str | None = None
    ) -> list[dict]:
        """按执行人查询 Task。"""
        self._check_auth(tenant_id, "wms:task:query")
        tasks = await self._task_repo.list_by_assignee(
            self._session, tenant_id, assignee_id, status
        )
        return [self._to_dict(t) for t in tasks]

    @staticmethod
    def _to_dict(task: WmsTaskORM) -> dict:
        return {
            "task_id": str(task.task_id),
            "task_type": task.task_type,
            "document_id": str(task.document_id),
            "document_type": task.document_type,
            "assignee_id": str(task.assignee_id) if task.assignee_id else None,
            "status": task.status,
            "priority": task.priority,
            "inv_transaction_ids": task.inv_transaction_ids,
            "created_at": task.created_at.isoformat() if task.created_at else None,
            "assigned_at": task.assigned_at.isoformat() if task.assigned_at else None,
            "started_at": task.started_at.isoformat() if task.started_at else None,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
        }