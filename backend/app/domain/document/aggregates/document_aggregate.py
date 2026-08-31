"""单据聚合根 - 七种单据类型状态机。

每种单据类型有独立的状态流转路径。
"""

from __future__ import annotations

from uuid import UUID

from app.domain.inventory.value_objects.shared import DocumentStatus, DocumentType
from app.domain.shared.aggregate_root import AggregateRoot
from app.domain.shared.entity import EntityId
from app.interfaces.middleware.error_handler import INVError, INVErrorCode


_DOCUMENT_STATE_MACHINES: dict[DocumentType, dict[DocumentStatus, set[DocumentStatus]]] = {
    DocumentType.PURCHASE_ORDER: {
        DocumentStatus.DRAFT: {DocumentStatus.SUBMITTED, DocumentStatus.CANCELLED},
        DocumentStatus.SUBMITTED: {DocumentStatus.APPROVED, DocumentStatus.REJECTED, DocumentStatus.CANCELLED},
        DocumentStatus.APPROVED: {DocumentStatus.RECEIVING, DocumentStatus.CANCELLED},
        DocumentStatus.RECEIVING: {DocumentStatus.COMPLETED},
        DocumentStatus.COMPLETED: set(),
        DocumentStatus.REJECTED: {DocumentStatus.DRAFT},
        DocumentStatus.CANCELLED: set(),
    },
    DocumentType.SALES_ORDER: {
        DocumentStatus.DRAFT: {DocumentStatus.SUBMITTED, DocumentStatus.CANCELLED},
        DocumentStatus.SUBMITTED: {DocumentStatus.APPROVED, DocumentStatus.REJECTED, DocumentStatus.CANCELLED},
        DocumentStatus.APPROVED: {DocumentStatus.PICKING, DocumentStatus.CANCELLED},
        DocumentStatus.PICKING: {DocumentStatus.SHIPPED},
        DocumentStatus.SHIPPED: {DocumentStatus.COMPLETED},
        DocumentStatus.COMPLETED: set(),
        DocumentStatus.REJECTED: {DocumentStatus.DRAFT},
        DocumentStatus.CANCELLED: set(),
    },
    DocumentType.RECEIPT: {
        DocumentStatus.DRAFT: {DocumentStatus.SUBMITTED, DocumentStatus.CANCELLED},
        DocumentStatus.SUBMITTED: {DocumentStatus.EXECUTING, DocumentStatus.CANCELLED},
        DocumentStatus.EXECUTING: {DocumentStatus.COMPLETED},
        DocumentStatus.COMPLETED: set(),
        DocumentStatus.CANCELLED: set(),
    },
    DocumentType.ISSUE: {
        DocumentStatus.DRAFT: {DocumentStatus.SUBMITTED, DocumentStatus.CANCELLED},
        DocumentStatus.SUBMITTED: {DocumentStatus.EXECUTING, DocumentStatus.CANCELLED},
        DocumentStatus.EXECUTING: {DocumentStatus.COMPLETED},
        DocumentStatus.COMPLETED: set(),
        DocumentStatus.CANCELLED: set(),
    },
    DocumentType.TRANSFER_ORDER: {
        DocumentStatus.DRAFT: {DocumentStatus.SUBMITTED, DocumentStatus.CANCELLED},
        DocumentStatus.SUBMITTED: {DocumentStatus.APPROVED, DocumentStatus.REJECTED, DocumentStatus.CANCELLED},
        DocumentStatus.APPROVED: {DocumentStatus.IN_TRANSIT, DocumentStatus.CANCELLED},
        DocumentStatus.IN_TRANSIT: {DocumentStatus.RECEIVED},
        DocumentStatus.RECEIVED: {DocumentStatus.COMPLETED},
        DocumentStatus.COMPLETED: set(),
        DocumentStatus.REJECTED: {DocumentStatus.DRAFT},
        DocumentStatus.CANCELLED: set(),
    },
    DocumentType.COUNT_ORDER: {
        DocumentStatus.DRAFT: {DocumentStatus.SUBMITTED, DocumentStatus.CANCELLED},
        DocumentStatus.SUBMITTED: {DocumentStatus.COUNTING, DocumentStatus.CANCELLED},
        DocumentStatus.COUNTING: {DocumentStatus.COUNTED},
        DocumentStatus.COUNTED: {DocumentStatus.DIFF_ANALYZED},
        DocumentStatus.DIFF_ANALYZED: {DocumentStatus.COMPLETED},
        DocumentStatus.COMPLETED: set(),
        DocumentStatus.CANCELLED: set(),
    },
    DocumentType.ADJUSTMENT_ORDER: {
        DocumentStatus.DRAFT: {DocumentStatus.SUBMITTED, DocumentStatus.CANCELLED},
        DocumentStatus.SUBMITTED: {DocumentStatus.APPROVED, DocumentStatus.REJECTED, DocumentStatus.CANCELLED},
        DocumentStatus.APPROVED: {DocumentStatus.EXECUTING, DocumentStatus.CANCELLED},
        DocumentStatus.EXECUTING: {DocumentStatus.COMPLETED},
        DocumentStatus.COMPLETED: set(),
        DocumentStatus.REJECTED: {DocumentStatus.DRAFT},
        DocumentStatus.CANCELLED: set(),
    },
}


class DocumentLine:
    """单据行。"""

    def __init__(
        self,
        line_id: EntityId,
        sku_id: UUID,
        quantity: float,
        unit_price: float | None = None,
        warehouse_id: UUID | None = None,
        location_id: UUID | None = None,
    ) -> None:
        self._line_id = line_id
        self._sku_id = sku_id
        self._quantity = quantity
        self._unit_price = unit_price
        self._warehouse_id = warehouse_id
        self._location_id = location_id

    @property
    def line_id(self) -> EntityId:
        return self._line_id

    @property
    def sku_id(self) -> UUID:
        return self._sku_id

    @property
    def quantity(self) -> float:
        return self._quantity

    @property
    def unit_price(self) -> float | None:
        return self._unit_price

    @property
    def warehouse_id(self) -> UUID | None:
        return self._warehouse_id

    @property
    def location_id(self) -> UUID | None:
        return self._location_id


class DocumentAggregate(AggregateRoot):
    """单据聚合根 - 统一封装七种单据类型。"""

    def __init__(
        self,
        id: EntityId,
        tenant_id: UUID,
        document_type: DocumentType,
        document_number: str,
        created_by: UUID,
        organization_id: UUID | None = None,
        site_id: UUID | None = None,
        warehouse_id: UUID | None = None,
        status: DocumentStatus = DocumentStatus.DRAFT,
        approved_by: UUID | None = None,
        executed_by: UUID | None = None,
    ) -> None:
        super().__init__(id)
        self._tenant_id = tenant_id
        self._document_type = document_type
        self._document_number = document_number
        self._created_by = created_by
        self._organization_id = organization_id
        self._site_id = site_id
        self._warehouse_id = warehouse_id
        self._status = status
        self._approved_by = approved_by
        self._executed_by = executed_by
        self._lines: list[DocumentLine] = []

    @property
    def tenant_id(self) -> UUID:
        return self._tenant_id

    @property
    def document_type(self) -> DocumentType:
        return self._document_type

    @property
    def document_number(self) -> str:
        return self._document_number

    @property
    def status(self) -> DocumentStatus:
        return self._status

    @property
    def created_by(self) -> UUID:
        return self._created_by

    @property
    def approved_by(self) -> UUID | None:
        return self._approved_by

    @property
    def executed_by(self) -> UUID | None:
        return self._executed_by

    @property
    def lines(self) -> list[DocumentLine]:
        return list(self._lines)

    def add_line(self, line: DocumentLine) -> None:
        self._lines.append(line)
        self._touch()

    def submit(self) -> None:
        self._transition(DocumentStatus.SUBMITTED)

    def approve(self, user_id: UUID) -> None:
        self._transition(DocumentStatus.APPROVED)
        self._approved_by = user_id

    def reject(self) -> None:
        self._transition(DocumentStatus.REJECTED)

    def execute(self, user_id: UUID) -> None:
        self._transition(DocumentStatus.EXECUTING)
        self._executed_by = user_id

    def complete(self) -> None:
        self._transition(DocumentStatus.COMPLETED)

    def cancel(self) -> None:
        self._transition(DocumentStatus.CANCELLED)

    def _transition(self, to_status: DocumentStatus) -> None:
        sm = _DOCUMENT_STATE_MACHINES.get(self._document_type, {})
        allowed = sm.get(self._status, set())
        if to_status not in allowed:
            raise INVError(
                INVErrorCode.INVALID_STATE_TRANSITION,
                f"单据 {self._document_type.value} 非法状态流转: "
                f"{self._status.value} → {to_status.value}",
            )
        self._status = to_status
        self._touch()

    def is_editable(self) -> bool:
        return self._status == DocumentStatus.DRAFT

    def is_deletable(self) -> bool:
        return self._status == DocumentStatus.DRAFT