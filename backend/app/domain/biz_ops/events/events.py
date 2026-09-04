"""BIZ-OPS 领域事件 - 7 类事件经 Outbox 异步发布。"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from uuid import UUID, uuid4


@dataclass(frozen=True)
class BizOpsDomainEvent:
    """BIZ-OPS 领域事件基类。"""
    event_id: UUID = field(default_factory=uuid4)
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    tenant_id: UUID | None = None
    trace_id: str | None = None

    @property
    def event_type(self) -> str:
        return self.__class__.__name__

    def to_outbox_payload(self) -> str:
        """序列化为 Outbox 载荷 JSON。"""
        d = asdict(self)
        for k, v in d.items():
            if isinstance(v, UUID):
                d[k] = str(v)
            elif isinstance(v, datetime):
                d[k] = v.isoformat()
        d["event_type"] = self.event_type
        return json.dumps(d, ensure_ascii=False, default=str)


@dataclass(frozen=True)
class BusinessOperationOrchestratedEvent(BizOpsDomainEvent):
    """业务操作编排完成事件。"""
    operation_type: str = ""
    operation_id: UUID | None = None
    result: str = ""


@dataclass(frozen=True)
class BusinessRuleTriggeredEvent(BizOpsDomainEvent):
    """业务规则触发事件。"""
    rule_key: str = ""
    rule_type: str = ""
    trigger_point: str = ""
    execution_result: str = ""


@dataclass(frozen=True)
class ApprovalFlowAdvancedEvent(BizOpsDomainEvent):
    """审批流推进事件。"""
    flow_id: UUID | None = None
    node_order: int = 0
    action: str = ""
    operator_id: UUID | None = None


@dataclass(frozen=True)
class PricingAppliedEvent(BizOpsDomainEvent):
    """定价应用事件。"""
    strategy_id: UUID | None = None
    strategy_type: str = ""
    base_price: float = 0.0
    final_price: float = 0.0


@dataclass(frozen=True)
class TaxCalculatedEvent(BizOpsDomainEvent):
    """税务计算完成事件 - FIN-001 可订阅。"""
    tax_config_id: UUID | None = None
    tax_type: str = ""
    tax_direction: str = ""
    tax_amount: float = 0.0
    net_amount: float = 0.0


@dataclass(frozen=True)
class InventoryStrategyTriggeredEvent(BizOpsDomainEvent):
    """库存策略触发事件。"""
    strategy_id: UUID | None = None
    strategy_type: str = ""
    sku_id: UUID | None = None
    warehouse_id: UUID | None = None


@dataclass(frozen=True)
class LinkageTriggeredEvent(BizOpsDomainEvent):
    """联动规则触发事件。"""
    rule_key: str = ""
    source_operation: str = ""
    linkage_action: str = ""
    async_executed: bool = True