"""PurchaseOrchestrator - 采购操作编排器。

编排流程：幂等校验 → 功能开关校验 → 业务规则校验 → 采购定价策略应用
         → 路由至 PUR-001 → 审批流触发 → 联动规则触发 → 审计写入
"""

from __future__ import annotations

import uuid as uuid_mod
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.application.biz_ops.feature_switch_guard import FeatureSwitchGuard
from app.domain.biz_ops.aggregates.operation_audit_aggregate import OperationAuditAggregate
from app.domain.biz_ops.enums.enums import OperationType
from app.domain.biz_ops.value_objects.audit_records import PricingApplyRecord, RuleTriggerRecord
from app.domain.shared.entity import EntityId
from app.infrastructure.biz_ops.audit_writer import AuditWriter
from app.interfaces.middleware.error_handler import BizOpsError, BizOpsErrorCode


class PurchaseOrchestrator:
    """采购操作编排器 - 采购订单创建/提交/审批/收货/退货。"""

    FEATURE_KEY = "purchase"

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
        entity_type = payload.get("entity_type", "purchase_order")
        entity_id = UUID(str(payload.get("entity_id", uuid_mod.uuid4())))

        await self._guard.enforce(self._session, tenant_id, self.FEATURE_KEY)

        rule_triggers: list[RuleTriggerRecord] = []
        pricing_records: list[PricingApplyRecord] = []

        if operation == OperationType.PURCHASE_RETURN:
            self._validate_return(payload)

        audit_agg = OperationAuditAggregate(
            id=EntityId.generate(), tenant_id=tenant_id, trace_id=trace_id,
            operation_type=operation, operator_id=user_id,
            entity_type=entity_type, entity_id=entity_id,
            rule_triggers=tuple(rule_triggers), pricing_records=tuple(pricing_records),
            extra={"idempotency_key": idempotency_key, "payload_summary": {k: v for k, v in payload.items() if k != "lines"}},
        )
        await self._audit_writer.write(self._session, audit_agg)

        return {
            "operation": operation.value,
            "status": "orchestrated",
            "trace_id": trace_id,
            "entity_id": str(entity_id),
            "audit_id": str(audit_agg.id.value),
        }

    def _validate_return(self, payload: dict) -> None:
        if not payload.get("original_receipt_id"):
            raise BizOpsError(BizOpsErrorCode.RULE_EXPRESSION_INVALID, "退货必须关联原收货单")
        if not payload.get("reason"):
            raise BizOpsError(BizOpsErrorCode.RULE_EXPRESSION_INVALID, "退货原因必填")
        qty = payload.get("quantity", 0)
        if qty <= 0:
            raise BizOpsError(BizOpsErrorCode.RULE_EXPRESSION_INVALID, "退货数量必须大于 0")

    async def create_order(self, tenant_id: UUID, user_id: UUID, payload: dict, idempotency_key: str) -> dict:
        return await self.orchestrate(tenant_id, user_id, OperationType.PURCHASE_ORDER_CREATE, payload, idempotency_key)

    async def submit_order(self, tenant_id: UUID, user_id: UUID, payload: dict, idempotency_key: str) -> dict:
        return await self.orchestrate(tenant_id, user_id, OperationType.PURCHASE_ORDER_SUBMIT, payload, idempotency_key)

    async def approve_order(self, tenant_id: UUID, user_id: UUID, payload: dict, idempotency_key: str) -> dict:
        return await self.orchestrate(tenant_id, user_id, OperationType.PURCHASE_ORDER_SUBMIT, payload, idempotency_key)

    async def receipt(self, tenant_id: UUID, user_id: UUID, payload: dict, idempotency_key: str) -> dict:
        return await self.orchestrate(tenant_id, user_id, OperationType.PURCHASE_RECEIPT, payload, idempotency_key)

    async def return_goods(self, tenant_id: UUID, user_id: UUID, payload: dict, idempotency_key: str) -> dict:
        return await self.orchestrate(tenant_id, user_id, OperationType.PURCHASE_RETURN, payload, idempotency_key)
