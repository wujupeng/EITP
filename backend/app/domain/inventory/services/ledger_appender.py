"""账本追加器 - 唯一允许向 InventoryLedger 追加记录的入口。

账本追加与余额更新在同一数据库事务内原子完成。
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.inventory.aggregates.inventory_balance_aggregate import InventoryBalanceAggregate
from app.domain.inventory.aggregates.inventory_ledger_aggregate import InventoryLedgerAggregate
from app.domain.inventory.value_objects.shared import TransactionType
from app.domain.shared.entity import EntityId
from app.interfaces.middleware.error_handler import INVError, INVErrorCode


class LedgerAppender:
    """账本追加器 - 校验字段完整性后追加，与余额更新原子完成。"""

    async def append(
        self,
        session: AsyncSession,
        balance: InventoryBalanceAggregate,
        transaction_id: UUID,
        tenant_id: UUID,
        sku_id: UUID,
        warehouse_id: UUID,
        transaction_type: TransactionType,
        quantity: float,
        operated_by: UUID,
        correlation_id: str | None = None,
        document_id: UUID | None = None,
        document_type: str | None = None,
        idempotency_key: str | None = None,
        organization_id: UUID | None = None,
        site_id: UUID | None = None,
        location_id: UUID | None = None,
        unit_cost: float | None = None,
        reason: str | None = None,
    ) -> InventoryLedgerAggregate:
        quantity_before = balance.on_hand
        direction_multiplier = -1.0 if transaction_type.value in (
            "sales_issue", "transfer_out", "adjustment_out",
            "return_out", "inspect_fail", "block",
        ) else 1.0
        actual_change = quantity * direction_multiplier
        quantity_after = quantity_before + actual_change

        ledger = InventoryLedgerAggregate(
            id=EntityId.generate(),
            transaction_id=transaction_id,
            tenant_id=tenant_id,
            sku_id=sku_id,
            warehouse_id=warehouse_id,
            transaction_type=transaction_type,
            quantity_before=quantity_before,
            quantity_change=actual_change,
            quantity_after=quantity_after,
            operated_by=operated_by,
            correlation_id=correlation_id,
            document_id=document_id,
            document_type=document_type,
            idempotency_key=idempotency_key,
            organization_id=organization_id,
            site_id=site_id,
            location_id=location_id,
            unit_cost=unit_cost,
            total_cost=unit_cost * quantity if unit_cost else None,
            reason=reason,
        )

        balance.apply_transaction(
            tx_type=transaction_type,
            quantity=quantity,
            ledger_id=ledger.id.value,
            unit_cost=unit_cost,
        )

        return ledger