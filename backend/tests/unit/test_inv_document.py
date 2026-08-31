"""EITP-INV-001 单据聚合根七种单据类型状态机单元测试。"""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.domain.document.aggregates.document_aggregate import DocumentAggregate, DocumentLine
from app.domain.inventory.value_objects.shared import DocumentStatus, DocumentType
from app.domain.shared.entity import EntityId
from app.interfaces.middleware.error_handler import INVError, INVErrorCode


@pytest.fixture
def tenant_id() -> uuid4:
    return uuid4()


@pytest.fixture
def created_by() -> uuid4:
    return uuid4()


def _make_document(
    *,
    tenant_id: uuid4 | None = None,
    document_type: DocumentType = DocumentType.PURCHASE_ORDER,
    document_number: str = "DOC-001",
    created_by: uuid4 | None = None,
    status: DocumentStatus = DocumentStatus.DRAFT,
) -> DocumentAggregate:
    return DocumentAggregate(
        id=EntityId.generate(),
        tenant_id=tenant_id or uuid4(),
        document_type=document_type,
        document_number=document_number,
        created_by=created_by or uuid4(),
        status=status,
    )


def _make_line(quantity: float = 10.0) -> DocumentLine:
    return DocumentLine(
        line_id=EntityId.generate(),
        sku_id=uuid4(),
        quantity=quantity,
        unit_price=5.0,
        warehouse_id=uuid4(),
    )


class DocumentAggregateTest:
    def test_create_purchase_order(
        self, tenant_id: uuid4, created_by: uuid4
    ) -> None:
        doc = DocumentAggregate(
            id=EntityId.generate(),
            tenant_id=tenant_id,
            document_type=DocumentType.PURCHASE_ORDER,
            document_number="PO-001",
            created_by=created_by,
        )
        assert doc.tenant_id == tenant_id
        assert doc.document_type == DocumentType.PURCHASE_ORDER
        assert doc.document_number == "PO-001"
        assert doc.created_by == created_by
        assert doc.status == DocumentStatus.DRAFT
        assert doc.approved_by is None
        assert doc.lines == []
        assert doc.is_editable() is True
        assert doc.is_deletable() is True

    @pytest.mark.parametrize(
        "doc_type",
        [
            DocumentType.PURCHASE_ORDER,
            DocumentType.SALES_ORDER,
            DocumentType.RECEIPT,
            DocumentType.ISSUE,
            DocumentType.TRANSFER_ORDER,
            DocumentType.COUNT_ORDER,
            DocumentType.ADJUSTMENT_ORDER,
        ],
    )
    def test_create_all_seven_document_types(self, doc_type: DocumentType) -> None:
        doc = _make_document(document_type=doc_type)
        assert doc.document_type == doc_type
        assert doc.status == DocumentStatus.DRAFT

    def test_purchase_order_full_lifecycle(
        self, tenant_id: uuid4, created_by: uuid4
    ) -> None:
        doc = _make_document(
            tenant_id=tenant_id,
            document_type=DocumentType.PURCHASE_ORDER,
            created_by=created_by,
        )
        doc.submit()
        assert doc.status == DocumentStatus.SUBMITTED
        approver = uuid4()
        doc.approve(approver)
        assert doc.status == DocumentStatus.APPROVED
        assert doc.approved_by == approver
        doc._transition(DocumentStatus.RECEIVING)
        assert doc.status == DocumentStatus.RECEIVING
        doc.complete()
        assert doc.status == DocumentStatus.COMPLETED

    def test_sales_order_full_lifecycle(self) -> None:
        doc = _make_document(document_type=DocumentType.SALES_ORDER)
        doc.submit()
        doc.approve(uuid4())
        doc._transition(DocumentStatus.PICKING)
        assert doc.status == DocumentStatus.PICKING
        doc._transition(DocumentStatus.SHIPPED)
        assert doc.status == DocumentStatus.SHIPPED
        doc.complete()
        assert doc.status == DocumentStatus.COMPLETED

    def test_transfer_order_full_lifecycle(self) -> None:
        doc = _make_document(document_type=DocumentType.TRANSFER_ORDER)
        doc.submit()
        doc.approve(uuid4())
        doc._transition(DocumentStatus.IN_TRANSIT)
        assert doc.status == DocumentStatus.IN_TRANSIT
        doc._transition(DocumentStatus.RECEIVED)
        assert doc.status == DocumentStatus.RECEIVED
        doc.complete()
        assert doc.status == DocumentStatus.COMPLETED

    def test_count_order_full_lifecycle(self) -> None:
        doc = _make_document(document_type=DocumentType.COUNT_ORDER)
        doc.submit()
        doc._transition(DocumentStatus.COUNTING)
        assert doc.status == DocumentStatus.COUNTING
        doc._transition(DocumentStatus.COUNTED)
        assert doc.status == DocumentStatus.COUNTED
        doc._transition(DocumentStatus.DIFF_ANALYZED)
        assert doc.status == DocumentStatus.DIFF_ANALYZED
        doc.complete()
        assert doc.status == DocumentStatus.COMPLETED

    def test_adjustment_order_full_lifecycle(self) -> None:
        doc = _make_document(document_type=DocumentType.ADJUSTMENT_ORDER)
        doc.submit()
        doc.approve(uuid4())
        executor = uuid4()
        doc.execute(executor)
        assert doc.status == DocumentStatus.EXECUTING
        assert doc.executed_by == executor
        doc.complete()
        assert doc.status == DocumentStatus.COMPLETED

    def test_receipt_full_lifecycle(self) -> None:
        doc = _make_document(document_type=DocumentType.RECEIPT)
        doc.submit()
        doc.execute(uuid4())
        doc.complete()
        assert doc.status == DocumentStatus.COMPLETED

    def test_issue_full_lifecycle(self) -> None:
        doc = _make_document(document_type=DocumentType.ISSUE)
        doc.submit()
        doc.execute(uuid4())
        doc.complete()
        assert doc.status == DocumentStatus.COMPLETED

    def test_illegal_transition_draft_to_completed_rejected(self) -> None:
        doc = _make_document(document_type=DocumentType.PURCHASE_ORDER)
        with pytest.raises(INVError) as exc:
            doc.complete()
        assert exc.value.code == INVErrorCode.INVALID_STATE_TRANSITION

    def test_illegal_transition_approved_to_completed_rejected(self) -> None:
        doc = _make_document(document_type=DocumentType.PURCHASE_ORDER)
        doc.submit()
        doc.approve(uuid4())
        with pytest.raises(INVError) as exc:
            doc.complete()
        assert exc.value.code == INVErrorCode.INVALID_STATE_TRANSITION

    def test_illegal_transition_count_order_approve_rejected(self) -> None:
        doc = _make_document(document_type=DocumentType.COUNT_ORDER)
        doc.submit()
        with pytest.raises(INVError) as exc:
            doc.approve(uuid4())
        assert exc.value.code == INVErrorCode.INVALID_STATE_TRANSITION

    def test_illegal_transition_completed_is_terminal(self) -> None:
        doc = _make_document(document_type=DocumentType.PURCHASE_ORDER)
        doc.submit()
        doc.approve(uuid4())
        doc._transition(DocumentStatus.RECEIVING)
        doc.complete()
        with pytest.raises(INVError) as exc:
            doc.cancel()
        assert exc.value.code == INVErrorCode.INVALID_STATE_TRANSITION

    def test_is_editable_only_true_for_draft(self) -> None:
        doc = _make_document(document_type=DocumentType.PURCHASE_ORDER)
        assert doc.is_editable() is True
        doc.submit()
        assert doc.is_editable() is False

    def test_is_deletable_only_true_for_draft(self) -> None:
        doc = _make_document(document_type=DocumentType.PURCHASE_ORDER)
        assert doc.is_deletable() is True
        doc.submit()
        assert doc.is_deletable() is False

    def test_approve_sets_approved_by(self) -> None:
        doc = _make_document(document_type=DocumentType.PURCHASE_ORDER)
        doc.submit()
        approver = uuid4()
        doc.approve(approver)
        assert doc.approved_by == approver

    def test_execute_sets_executed_by(self) -> None:
        doc = _make_document(document_type=DocumentType.ADJUSTMENT_ORDER)
        doc.submit()
        doc.approve(uuid4())
        executor = uuid4()
        doc.execute(executor)
        assert doc.executed_by == executor

    def test_add_line_appends_to_document(self) -> None:
        doc = _make_document(document_type=DocumentType.PURCHASE_ORDER)
        line = _make_line(quantity=20.0)
        doc.add_line(line)
        assert len(doc.lines) == 1
        assert doc.lines[0].quantity == 20.0
        assert doc.lines[0].unit_price == 5.0

    def test_document_line_properties_access(self) -> None:
        line_id = EntityId.generate()
        sku_id = uuid4()
        warehouse_id = uuid4()
        location_id = uuid4()
        line = DocumentLine(
            line_id=line_id,
            sku_id=sku_id,
            quantity=15.0,
            unit_price=7.0,
            warehouse_id=warehouse_id,
            location_id=location_id,
        )
        assert line.line_id == line_id
        assert line.sku_id == sku_id
        assert line.quantity == 15.0
        assert line.unit_price == 7.0
        assert line.warehouse_id == warehouse_id
        assert line.location_id == location_id

    def test_reject_then_back_to_draft(self) -> None:
        doc = _make_document(document_type=DocumentType.PURCHASE_ORDER)
        doc.submit()
        doc.reject()
        assert doc.status == DocumentStatus.REJECTED
        doc._transition(DocumentStatus.DRAFT)
        assert doc.status == DocumentStatus.DRAFT
        assert doc.is_editable() is True

    def test_cancel_from_draft(self) -> None:
        doc = _make_document(document_type=DocumentType.PURCHASE_ORDER)
        doc.cancel()
        assert doc.status == DocumentStatus.CANCELLED
        assert doc.is_editable() is False
        assert doc.is_deletable() is False