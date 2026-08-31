"""库存账本聚合根 - append-only 事实源，不可变。

P0 原则：Ledger 是系统事实源，每条记录包含完整审计信息。
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from app.domain.inventory.value_objects.shared import Direction, TransactionType, direction_of
from app.domain.shared.aggregate_root import AggregateRoot
from app.domain.shared.entity import EntityId
from app.interfaces.middleware.error_handler import INVError, INVErrorCode


class InventoryLedgerAggregate(AggregateRoot):
    """库存账本聚合根 - append-only，禁止修改/删除。

    每条记录包含：事务标识、单据标识、幂等键、四级归属、SKU、
    事务类型、方向、变化前/变化量/变化后、成本、操作人、操作时间。
    """

    def __init__(
        self,
        id: EntityId,
        transaction_id: UUID,
        tenant_id: UUID,
        sku_id: UUID,
        warehouse_id: UUID,
        transaction_type: TransactionType,
        quantity_before: float,
        quantity_change: float,
        quantity_after: float,
        operated_by: UUID,
        correlation_id: str | None = None,
        document_id: UUID | None = None,
        document_type: str | None = None,
        idempotency_key: str | None = None,
        organization_id: UUID | None = None,
        site_id: UUID | None = None,
        location_id: UUID | None = None,
        unit_cost: float | None = None,
        total_cost: float | None = None,
        reason: str | None = None,
        operated_at: datetime | None = None,
    ) -> None:
        super().__init__(id)
        self._validate_required_fields(
            transaction_id, tenant_id, sku_id, warehouse_id,
            transaction_type, quantity_before, quantity_change, quantity_after,
            operated_by,
        )
        self._check_quantity_consistency(quantity_before, quantity_change, quantity_after)
        self._transaction_id = transaction_id
        self._correlation_id = correlation_id
        self._document_id = document_id
        self._document_type = document_type
        self._idempotency_key = idempotency_key
        self._tenant_id = tenant_id
        self._organization_id = organization_id
        self._site_id = site_id
        self._warehouse_id = warehouse_id
        self._location_id = location_id
        self._sku_id = sku_id
        self._transaction_type = transaction_type
        self._direction = direction_of(transaction_type)
        self._quantity_before = quantity_before
        self._quantity_change = quantity_change
        self._quantity_after = quantity_after
        self._unit_cost = unit_cost
        self._total_cost = total_cost
        self._reason = reason
        self._operated_by = operated_by
        self._operated_at = operated_at or datetime.now(timezone.utc)

    def _validate_required_fields(
        self,
        transaction_id: UUID,
        tenant_id: UUID,
        sku_id: UUID,
        warehouse_id: UUID,
        transaction_type: TransactionType,
        quantity_before: float,
        quantity_change: float,
        quantity_after: float,
        operated_by: UUID,
    ) -> None:
        missing: list[str] = []
        if transaction_id is None:
            missing.append("transaction_id")
        if tenant_id is None:
            missing.append("tenant_id")
        if sku_id is None:
            missing.append("sku_id")
        if warehouse_id is None:
            missing.append("warehouse_id")
        if transaction_type is None:
            missing.append("transaction_type")
        if operated_by is None:
            missing.append("operated_by")
        if missing:
            raise INVError(
                INVErrorCode.LEDGER_FIELD_REQUIRED,
                f"账本必填字段缺失: {', '.join(missing)}",
            )

    def _check_quantity_consistency(
        self, before: float, change: float, after: float
    ) -> None:
        if abs((before + change) - after) > 0.0001:
            raise INVError(
                INVErrorCode.LEDGER_FIELD_REQUIRED,
                f"数量不一致: {before} + {change} != {after}",
            )

    @property
    def transaction_id(self) -> UUID:
        return self._transaction_id

    @property
    def correlation_id(self) -> str | None:
        return self._correlation_id

    @property
    def document_id(self) -> UUID | None:
        return self._document_id

    @property
    def document_type(self) -> str | None:
        return self._document_type

    @property
    def idempotency_key(self) -> str | None:
        return self._idempotency_key

    @property
    def tenant_id(self) -> UUID:
        return self._tenant_id

    @property
    def organization_id(self) -> UUID | None:
        return self._organization_id

    @property
    def site_id(self) -> UUID | None:
        return self._site_id

    @property
    def warehouse_id(self) -> UUID:
        return self._warehouse_id

    @property
    def location_id(self) -> UUID | None:
        return self._location_id

    @property
    def sku_id(self) -> UUID:
        return self._sku_id

    @property
    def transaction_type(self) -> TransactionType:
        return self._transaction_type

    @property
    def direction(self) -> Direction:
        return self._direction

    @property
    def quantity_before(self) -> float:
        return self._quantity_before

    @property
    def quantity_change(self) -> float:
        return self._quantity_change

    @property
    def quantity_after(self) -> float:
        return self._quantity_after

    @property
    def unit_cost(self) -> float | None:
        return self._unit_cost

    @property
    def total_cost(self) -> float | None:
        return self._total_cost

    @property
    def reason(self) -> str | None:
        return self._reason

    @property
    def operated_by(self) -> UUID:
        return self._operated_by

    @property
    def operated_at(self) -> datetime:
        return self._operated_at