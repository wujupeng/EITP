"""WarehouseOrchestrator - 仓库操作编排器。

编排流程：功能开关校验 → 业务规则校验 → 路由至 WMS-001
         → 异步联动规则触发 → 审计写入
"""

from __future__ import annotations

import uuid as uuid_mod
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.application.biz_ops.feature_switch_guard import FeatureSwitchGuard
from app.domain.biz_ops.aggregates.operation_audit_aggregate import OperationAuditAggregate
from app.domain.biz_ops.enums.enums import OperationType
from app.domain.shared.entity import EntityId
from app.infrastructure.biz_ops.audit_writer import AuditWriter


class WarehouseOrchestrator:
    """仓库操作编排器 - 收货/上架/拣货/移库/发货。"""

    FEATURE_KEY = "warehouse"

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._guard = FeatureSwitchGuard()
        self._audit_writer = AuditWriter()

    async def orchestrate(
        self,
        tenant_id: UUID,
        user_id: UUID,
        operation: OperationType,
        payload: dict,
        idempotency_key: str,
    ) -> dict:
        trace_id = idempotency_key or uuid_mod.uuid4().hex
        entity_type = payload.get("entity_type", "warehouse_task")
        entity_id = UUID(str(payload.get("entity_id", uuid_mod.uuid4())))

        await self._guard.enforce(self._session, tenant_id, self.FEATURE_KEY)

        linkage_suggestions = self._get_linkage_suggestions(operation, payload)

        audit_agg = OperationAuditAggregate(
            id=EntityId.generate(), tenant_id=tenant_id, trace_id=trace_id,
            operation_type=operation, operator_id=user_id,
            entity_type=entity_type, entity_id=entity_id,
            extra={"idempotency_key": idempotency_key, "linkage_suggestions": linkage_suggestions},
        )
        await self._audit_writer.write(self._session, audit_agg)

        return {
            "operation": operation.value,
            "status": "orchestrated",
            "trace_id": trace_id,
            "entity_id": str(entity_id),
            "audit_id": str(audit_agg.id.value),
            "linkage_suggestions": linkage_suggestions,
        }

    def _get_linkage_suggestions(self, operation: OperationType, payload: dict) -> list[str]:
        suggestions: list[str] = []
        if operation == OperationType.WAREHOUSE_RECEIVING:
            suggestions.append("建议上架")
            suggestions.append("建议质检")
        elif operation == OperationType.WAREHOUSE_PICKING:
            suggestions.append("建议打包")
        elif operation == OperationType.WAREHOUSE_SHIPPING:
            suggestions.append("建议物流跟踪")
            suggestions.append("建议通知客户")
        return suggestions

    async def receiving(self, tenant_id: UUID, user_id: UUID, payload: dict, idempotency_key: str) -> dict:
        return await self.orchestrate(tenant_id, user_id, OperationType.WAREHOUSE_RECEIVING, payload, idempotency_key)

    async def putaway(self, tenant_id: UUID, user_id: UUID, payload: dict, idempotency_key: str) -> dict:
        return await self.orchestrate(tenant_id, user_id, OperationType.WAREHOUSE_PUTAWAY, payload, idempotency_key)

    async def picking(self, tenant_id: UUID, user_id: UUID, payload: dict, idempotency_key: str) -> dict:
        return await self.orchestrate(tenant_id, user_id, OperationType.WAREHOUSE_PICKING, payload, idempotency_key)

    async def transfer(self, tenant_id: UUID, user_id: UUID, payload: dict, idempotency_key: str) -> dict:
        return await self.orchestrate(tenant_id, user_id, OperationType.WAREHOUSE_TRANSFER, payload, idempotency_key)

    async def shipping(self, tenant_id: UUID, user_id: UUID, payload: dict, idempotency_key: str) -> dict:
        return await self.orchestrate(tenant_id, user_id, OperationType.WAREHOUSE_SHIPPING, payload, idempotency_key)
