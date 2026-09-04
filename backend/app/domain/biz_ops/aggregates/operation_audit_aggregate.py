"""OperationAuditAggregate - 业务操作审计聚合根。"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from app.domain.biz_ops.enums.enums import OperationType
from app.domain.biz_ops.value_objects.audit_records import (
    CreditCheckResult,
    PricingApplyRecord,
    RuleTriggerRecord,
    StrategyTriggerRecord,
    TaxCalcResultRecord,
)
from app.domain.shared.aggregate_root import AggregateRoot
from app.domain.shared.entity import EntityId


class OperationAuditAggregate(AggregateRoot):
    """业务操作审计聚合根 - append-only，记录完整操作编排链路。"""

    def __init__(
        self,
        id: EntityId,
        tenant_id: UUID,
        trace_id: str,
        operation_type: OperationType,
        operator_id: UUID,
        entity_type: str,
        entity_id: UUID,
        occurred_at: datetime | None = None,
        rule_triggers: tuple[RuleTriggerRecord, ...] = (),
        pricing_records: tuple[PricingApplyRecord, ...] = (),
        tax_records: tuple[TaxCalcResultRecord, ...] = (),
        strategy_triggers: tuple[StrategyTriggerRecord, ...] = (),
        credit_check: CreditCheckResult | None = None,
        approval_flow_id: UUID | None = None,
        approval_action: str | None = None,
        extra: dict | None = None,
    ) -> None:
        super().__init__(id)
        self._tenant_id = tenant_id
        self._trace_id = trace_id
        self._operation_type = operation_type
        self._operator_id = operator_id
        self._entity_type = entity_type
        self._entity_id = entity_id
        self._occurred_at = occurred_at or datetime.now(timezone.utc)
        self._rule_triggers = rule_triggers
        self._pricing_records = pricing_records
        self._tax_records = tax_records
        self._strategy_triggers = strategy_triggers
        self._credit_check = credit_check
        self._approval_flow_id = approval_flow_id
        self._approval_action = approval_action
        self._extra = extra or {}

    @property
    def tenant_id(self) -> UUID: return self._tenant_id
    @property
    def trace_id(self) -> str: return self._trace_id
    @property
    def operation_type(self) -> OperationType: return self._operation_type
    @property
    def operator_id(self) -> UUID: return self._operator_id
    @property
    def entity_type(self) -> str: return self._entity_type
    @property
    def entity_id(self) -> UUID: return self._entity_id
    @property
    def occurred_at(self) -> datetime: return self._occurred_at
    @property
    def rule_triggers(self) -> tuple[RuleTriggerRecord, ...]: return self._rule_triggers
    @property
    def pricing_records(self) -> tuple[PricingApplyRecord, ...]: return self._pricing_records
    @property
    def tax_records(self) -> tuple[TaxCalcResultRecord, ...]: return self._tax_records
    @property
    def strategy_triggers(self) -> tuple[StrategyTriggerRecord, ...]: return self._strategy_triggers
    @property
    def credit_check(self) -> CreditCheckResult | None: return self._credit_check
    @property
    def approval_flow_id(self) -> UUID | None: return self._approval_flow_id
    @property
    def approval_action(self) -> str | None: return self._approval_action
    @property
    def extra(self) -> dict: return self._extra

    def to_dict(self) -> dict:
        """序列化为字典（用于持久化）。"""
        import json
        return {
            "trace_id": self._trace_id,
            "operation_type": self._operation_type.value,
            "operator_id": str(self._operator_id),
            "entity_type": self._entity_type,
            "entity_id": str(self._entity_id),
            "occurred_at": self._occurred_at.isoformat(),
            "rule_triggers": [
                {"rule_key": r.rule_key, "rule_type": r.rule_type,
                 "trigger_point": r.trigger_point, "result": r.result, "message": r.message}
                for r in self._rule_triggers
            ],
            "pricing_records": [
                {"strategy_id": str(p.strategy_id), "strategy_type": p.strategy_type,
                 "base_price": p.base_price, "final_price": p.final_price}
                for p in self._pricing_records
            ],
            "tax_records": [
                {"config_key": t.config_key, "total_tax": t.total_tax, "total_amount": t.total_amount}
                for t in self._tax_records
            ],
            "strategy_triggers": [
                {"strategy_id": str(s.strategy_id), "strategy_type": s.strategy_type,
                 "target_ref": s.target_ref, "result": s.result, "message": s.message, "suggestion": s.suggestion}
                for s in self._strategy_triggers
            ],
            "credit_check": {
                "customer_id": str(self._credit_check.customer_id),
                "used_amount": self._credit_check.used_amount,
                "credit_limit": self._credit_check.credit_limit,
                "passed": self._credit_check.passed,
                "message": self._credit_check.message,
            } if self._credit_check else None,
            "approval_flow_id": str(self._approval_flow_id) if self._approval_flow_id else None,
            "approval_action": self._approval_action,
            "extra": self._extra,
        }