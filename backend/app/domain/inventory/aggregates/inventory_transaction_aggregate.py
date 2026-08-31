"""库存事务聚合根 - 12 种事务类型 + 状态机 + 幂等键。

状态流转：pending → executing → completed/failed/cancelled
"""

from __future__ import annotations

from uuid import UUID

from app.domain.inventory.value_objects.shared import (
    Direction,
    TransactionStatus,
    TransactionType,
    direction_of,
)
from app.domain.shared.aggregate_root import AggregateRoot
from app.domain.shared.entity import EntityId
from app.interfaces.middleware.error_handler import INVError, INVErrorCode


_VALID_TRANSITIONS: dict[TransactionStatus, set[TransactionStatus]] = {
    TransactionStatus.PENDING: {
        TransactionStatus.EXECUTING,
        TransactionStatus.CANCELLED,
    },
    TransactionStatus.EXECUTING: {
        TransactionStatus.COMPLETED,
        TransactionStatus.FAILED,
    },
    TransactionStatus.COMPLETED: set(),
    TransactionStatus.FAILED: {TransactionStatus.PENDING},
    TransactionStatus.CANCELLED: set(),
}


class InventoryTransactionAggregate(AggregateRoot):
    """库存事务聚合根 - 封装事务标识、归属、类型、数量、状态。"""

    def __init__(
        self,
        id: EntityId,
        tenant_id: UUID,
        sku_id: UUID,
        warehouse_id: UUID,
        transaction_type: TransactionType,
        quantity: float,
        idempotency_key: str,
        correlation_id: str | None = None,
        document_id: UUID | None = None,
        document_type: str | None = None,
        organization_id: UUID | None = None,
        site_id: UUID | None = None,
        location_id: UUID | None = None,
        status: TransactionStatus = TransactionStatus.PENDING,
        result_ledger_id: UUID | None = None,
    ) -> None:
        super().__init__(id)
        if quantity <= 0:
            raise INVError(
                INVErrorCode.LEDGER_FIELD_REQUIRED,
                "事务数量必须为正数",
            )
        if not idempotency_key:
            raise INVError(
                INVErrorCode.IDEMPOTENCY_KEY_REQUIRED,
                "幂等键不能为空",
            )
        self._tenant_id = tenant_id
        self._sku_id = sku_id
        self._warehouse_id = warehouse_id
        self._transaction_type = transaction_type
        self._direction = direction_of(transaction_type)
        self._quantity = quantity
        self._idempotency_key = idempotency_key
        self._correlation_id = correlation_id
        self._document_id = document_id
        self._document_type = document_type
        self._organization_id = organization_id
        self._site_id = site_id
        self._location_id = location_id
        self._status = status
        self._result_ledger_id = result_ledger_id

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
    def transaction_type(self) -> TransactionType:
        return self._transaction_type

    @property
    def direction(self) -> Direction:
        return self._direction

    @property
    def quantity(self) -> float:
        return self._quantity

    @property
    def idempotency_key(self) -> str:
        return self._idempotency_key

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
    def organization_id(self) -> UUID | None:
        return self._organization_id

    @property
    def site_id(self) -> UUID | None:
        return self._site_id

    @property
    def location_id(self) -> UUID | None:
        return self._location_id

    @property
    def status(self) -> TransactionStatus:
        return self._status

    @property
    def result_ledger_id(self) -> UUID | None:
        return self._result_ledger_id

    def execute(self) -> None:
        self._transition(TransactionStatus.EXECUTING)

    def complete(self, ledger_id: UUID) -> None:
        self._transition(TransactionStatus.COMPLETED)
        self._result_ledger_id = ledger_id

    def fail(self) -> None:
        self._transition(TransactionStatus.FAILED)

    def cancel(self) -> None:
        self._transition(TransactionStatus.CANCELLED)

    def _transition(self, to_status: TransactionStatus) -> None:
        allowed = _VALID_TRANSITIONS.get(self._status, set())
        if to_status not in allowed:
            raise INVError(
                INVErrorCode.INVALID_STATE_TRANSITION,
                f"非法状态流转: {self._status.value} → {to_status.value}",
            )
        self._status = to_status
        self._touch()

    def is_outbound(self) -> bool:
        return self._direction == Direction.OUTBOUND

    def is_inbound(self) -> bool:
        return self._direction == Direction.INBOUND