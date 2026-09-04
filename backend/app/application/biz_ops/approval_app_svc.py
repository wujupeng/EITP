"""ApprovalAppSvc - 审批操作应用服务。"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.biz_ops.services.approval_orchestrator import ApprovalOrchestrator
from app.infrastructure.biz_ops.repositories.approval_flow_repository import ApprovalFlowRepository


class ApprovalAppSvc:
    """审批操作应用服务。"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._flow_repo = ApprovalFlowRepository()
        self._orchestrator = ApprovalOrchestrator()

    async def process_approval(
        self, tenant_id: UUID, user_id: UUID, approval_id: UUID,
        flow_id: UUID, node_order: int, action: str, comment: str = "",
    ) -> dict:
        await self._flow_repo.add_record(
            self._session, tenant_id, approval_id, flow_id, node_order, action, user_id, comment
        )
        await self._session.commit()
        return {"approval_id": str(approval_id), "action": action, "status": "processed"}