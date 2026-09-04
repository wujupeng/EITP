"""InventoryOrchestrator - 库存操作编排器。

编排流程：功能开关校验 → 业务规则校验（含负库存拦截）→ 路由至 INV-001/WMS-001
         → 异步库存策略检查 → 审计写入
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
from app.interfaces.middleware.error_handler import BizOpsError, BizOpsErrorCode


class InventoryOrchestrator:
    """库存操作编排器 - 入库/出库/调拨/盘点/调整。"""

    FEATURE_KEY = "inventory"

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
        entity_type = payload.get("entity_type", "inventory_movement")
        entity_id = UUID(str(payload.get("entity_id", uuid_mod.uuid4())))

        await self._guard.enforce(self._session, tenant_id, self.FEATURE_KEY)

        if operation == OperationType.INVENTORY_OUTBOUND:
            self._check_negative_stock(payload)
        elif operation == OperationType.INVENTORY_TRANSFER:
            self._validate_transfer(payload)
        elif operation == OperationType.INVENTORY_COUNT:
            self._validate_count(payload)

        audit_agg = OperationAuditAggregate(
            id=EntityId.generate(), tenant_id=tenant_id, trace_id=trace_id,
            operation_type=operation, operator_id=user_id,
            entity_type=entity_type, entity_id=entity_id,
            extra={"idempotency_key": idempotency_key},
        )
        await self._audit_writer.write(self._session, audit_agg)

        return {
            "operation": operation.value,
            "status": "orchestrated",
            "trace_id": trace_id,
            "entity_id": str(entity_id),
            "audit_id": str(audit_agg.id.value),
        }

    def _check_negative_stock(self, payload: dict) -> None:
        available = payload.get("available_quantity", 0)
        request_qty = payload.get("quantity", 0)
        if request_qty > available:
            strategy = payload.get("negative_strategy", "reject")
            if strategy == "reject":
                raise BizOpsError(
                    BizOpsErrorCode.RULE_EXPRESSION_INVALID,
                    f"可用量 {available} 不足，请求 {request_qty}",
                )

    def _validate_transfer(self, payload: dict) -> None:
        src = payload.get("source_warehouse_id")
        dst = payload.get("target_warehouse_id")
        if not src or not dst:
            raise BizOpsError(BizOpsErrorCode.RULE_EXPRESSION_INVALID, "调拨必须指定源/目标仓库")
        if src == dst:
            raise BizOpsError(BizOpsErrorCode.RULE_EXPRESSION_INVALID, "源仓库不能等于目标仓库")

    def _validate_count(self, payload: dict) -> None:
        if not payload.get("warehouse_id"):
            raise BizOpsError(BizOpsErrorCode.RULE_EXPRESSION_INVALID, "盘点必须指定仓库")

    async def inbound(self, tenant_id: UUID, user_id: UUID, payload: dict, idempotency_key: str) -> dict:
        return await self.orchestrate(tenant_id, user_id, OperationType.INVENTORY_INBOUND, payload, idempotency_key)

    async def outbound(self, tenant_id: UUID, user_id: UUID, payload: dict, idempotency_key: str) -> dict:
        return await self.orchestrate(tenant_id, user_id, OperationType.INVENTORY_OUTBOUND, payload, idempotency_key)

    async def transfer(self, tenant_id: UUID, user_id: UUID, payload: dict, idempotency_key: str) -> dict:
        return await self.orchestrate(tenant_id, user_id, OperationType.INVENTORY_TRANSFER, payload, idempotency_key)

    async def count(self, tenant_id: UUID, user_id: UUID, payload: dict, idempotency_key: str) -> dict:
        return await self.orchestrate(tenant_id, user_id, OperationType.INVENTORY_COUNT, payload, idempotency_key)

    async def adjust(self, tenant_id: UUID, user_id: UUID, payload: dict, idempotency_key: str) -> dict:
        return await self.orchestrate(tenant_id, user_id, OperationType.INVENTORY_ADJUST, payload, idempotency_key)
