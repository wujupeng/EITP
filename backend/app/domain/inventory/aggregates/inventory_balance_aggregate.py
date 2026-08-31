"""库存余额聚合根 - 六状态量快照。

P0 原则：Balance 是从 Ledger 计算的快照，available = on_hand - reserved。
所有更新必须通过 apply_transaction 触发，禁止直接修改。
"""

from __future__ import annotations

from uuid import UUID

from app.domain.inventory.value_objects.shared import TransactionType
from app.domain.shared.aggregate_root import AggregateRoot
from app.domain.shared.entity import EntityId
from app.interfaces.middleware.error_handler import INVError, INVErrorCode


class InventoryBalanceAggregate(AggregateRoot):
    """库存余额聚合根 - 六状态量快照。

    on_hand: 现有量
    reserved: 预留量
    available: 可用量 = on_hand - reserved（系统计算）
    in_transit: 在途量
    inspection: 待检量
    blocked: 冻结量
    """

    def __init__(
        self,
        id: EntityId,
        tenant_id: UUID,
        sku_id: UUID,
        warehouse_id: UUID,
        location_id: UUID | None = None,
        batch_no: str | None = None,
        on_hand: float = 0.0,
        reserved: float = 0.0,
        in_transit: float = 0.0,
        inspection: float = 0.0,
        blocked: float = 0.0,
        unit_cost: float = 0.0,
        last_ledger_id: UUID | None = None,
    ) -> None:
        super().__init__(id)
        self._tenant_id = tenant_id
        self._sku_id = sku_id
        self._warehouse_id = warehouse_id
        self._location_id = location_id
        self._batch_no = batch_no
        self._on_hand = on_hand
        self._reserved = reserved
        self._in_transit = in_transit
        self._inspection = inspection
        self._blocked = blocked
        self._unit_cost = unit_cost
        self._last_ledger_id = last_ledger_id

    @property
    def tenant_id(self) -> UUID:
        return self._tenant_id

    @property
    def sku_id(self) -> UUID:
        return self._sku_id

    @property
    def warehouse_id(self) -> UUID:
        return self._warehouse_id

    @property
    def location_id(self) -> UUID | None:
        return self._location_id

    @property
    def batch_no(self) -> str | None:
        return self._batch_no

    @property
    def on_hand(self) -> float:
        return self._on_hand

    @property
    def reserved(self) -> float:
        return self._reserved

    @property
    def available(self) -> float:
        return self._on_hand - self._reserved

    @property
    def in_transit(self) -> float:
        return self._in_transit

    @property
    def inspection(self) -> float:
        return self._inspection

    @property
    def blocked(self) -> float:
        return self._blocked

    @property
    def unit_cost(self) -> float:
        return self._unit_cost

    @property
    def last_ledger_id(self) -> UUID | None:
        return self._last_ledger_id

    def recompute_available(self) -> float:
        return self._on_hand - self._reserved

    def apply_transaction(
        self,
        tx_type: TransactionType,
        quantity: float,
        ledger_id: UUID,
        unit_cost: float | None = None,
    ) -> None:
        """按 12 种事务类型更新六状态量。仅由库存事务触发。"""
        if quantity <= 0:
            raise INVError(
                INVErrorCode.LEDGER_FIELD_REQUIRED,
                "事务数量必须为正数",
            )

        if tx_type == TransactionType.PURCHASE_RECEIPT:
            self._on_hand += quantity
        elif tx_type == TransactionType.SALES_ISSUE:
            self._on_hand -= quantity
        elif tx_type == TransactionType.TRANSFER_OUT:
            self._on_hand -= quantity
            self._in_transit += quantity
        elif tx_type == TransactionType.TRANSFER_IN:
            self._in_transit -= quantity
            self._on_hand += quantity
        elif tx_type == TransactionType.ADJUSTMENT_IN:
            self._on_hand += quantity
        elif tx_type == TransactionType.ADJUSTMENT_OUT:
            self._on_hand -= quantity
        elif tx_type == TransactionType.RETURN_IN:
            self._on_hand += quantity
        elif tx_type == TransactionType.RETURN_OUT:
            self._on_hand -= quantity
        elif tx_type == TransactionType.INSPECT_PASS:
            self._inspection -= quantity
            self._on_hand += quantity
        elif tx_type == TransactionType.INSPECT_FAIL:
            self._inspection -= quantity
        elif tx_type == TransactionType.BLOCK:
            self._on_hand -= quantity
            self._blocked += quantity
        elif tx_type == TransactionType.UNBLOCK:
            self._blocked -= quantity
            self._on_hand += quantity

        if unit_cost is not None:
            self._unit_cost = unit_cost
        self._last_ledger_id = ledger_id
        self._touch()

    def add_reservation(self, quantity: float) -> None:
        if quantity <= 0:
            return
        if self.available < quantity:
            raise INVError(
                INVErrorCode.INSUFFICIENT_AVAILABLE,
                f"可用量不足: {self.available} < {quantity}",
            )
        self._reserved += quantity
        self._touch()

    def release_reservation(self, quantity: float) -> None:
        if quantity <= 0:
            return
        release = min(quantity, self._reserved)
        self._reserved -= release
        self._touch()

    def consume_reservation(self, quantity: float) -> None:
        if quantity <= 0:
            return
        consume = min(quantity, self._reserved)
        self._reserved -= consume
        self._touch()