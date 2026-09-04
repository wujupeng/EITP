"""LinkageActionHandler - 联动规则处理器。"""

from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID


class LinkageActionHandler(ABC):
    """联动动作处理器抽象接口。"""

    @abstractmethod
    async def handle(self, tenant_id: UUID, context: dict) -> dict:
        """执行联动动作 - 异步执行，失败不影响主操作。"""
        ...


class QualityCheckHandler(LinkageActionHandler):
    """采购到货 → 质检联动。"""

    async def handle(self, tenant_id: UUID, context: dict) -> dict:
        return {"linkage": "quality_check", "status": "triggered", "tenant_id": str(tenant_id)}


class CostTransferHandler(LinkageActionHandler):
    """销售发货 → 成本结转联动。"""

    async def handle(self, tenant_id: UUID, context: dict) -> dict:
        return {"linkage": "cost_transfer", "status": "triggered", "tenant_id": str(tenant_id)}


class ReplenishSuggestionHandler(LinkageActionHandler):
    """库存低于安全库存 → 补货建议联动。"""

    async def handle(self, tenant_id: UUID, context: dict) -> dict:
        return {"linkage": "replenish_suggestion", "status": "triggered", "tenant_id": str(tenant_id)}


_LINKAGE_HANDLERS: dict[str, LinkageActionHandler] = {
    "quality_check": QualityCheckHandler(),
    "cost_transfer": CostTransferHandler(),
    "replenish_suggestion": ReplenishSuggestionHandler(),
}


def get_linkage_handler(action: str) -> LinkageActionHandler | None:
    return _LINKAGE_HANDLERS.get(action)