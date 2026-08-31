"""移库单聚合根 - 同仓库内库位间移动，含审批流转。"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from uuid import UUID

from app.domain.shared.aggregate_root import AggregateRoot
from app.domain.shared.entity import EntityId
from app.domain.warehouse.entities.transfer_line import TransferLine
from app.interfaces.middleware.error_handler import WMSError, WMSErrorCode


class TransferStatus(str, Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXECUTING = "executing"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class TransferOrderAggregate(AggregateRoot):
    """移库单聚合根 - 同仓库内库位间移动。

    跨仓库拒绝 EITP_WMS_TRANSFER_CROSS_WAREHOUSE（spec 5.6.1.8）。
    移库通过 INV Transaction TRANSFER_OUT+TRANSFER_IN 落地。
    """

    def __init__(
        self,
        id: EntityId,
        tenant_id: UUID,
        warehouse_id: UUID,
        require_approval: bool = False,
    ) -> None:
        super().__init__(id)
        self._tenant_id = tenant_id
        self._warehouse_id = warehouse_id
        self._status = TransferStatus.DRAFT
        self._lines: list[TransferLine] = []
        self._require_approval = require_approval
        self._approver_id: UUID | None = None
        self._approved_at: datetime | None = None
        self._approval_opinion: str | None = None
        self._inv_transaction_ids: list[UUID] = []

    @property
    def tenant_id(self) -> UUID:
        return self._tenant_id

    @property
    def warehouse_id(self) -> UUID:
        return self._warehouse_id

    @property
    def status(self) -> TransferStatus:
        return self._status

    @property
    def lines(self) -> list[TransferLine]:
        return list(self._lines)

    @property
    def require_approval(self) -> bool:
        return self._require_approval

    @property
    def approver_id(self) -> UUID | None:
        return self._approver_id

    @property
    def inv_transaction_ids(self) -> list[UUID]:
        return list(self._inv_transaction_ids)

    def add_line(
        self,
        sku_id: UUID,
        source_location_id: UUID,
        target_location_id: UUID,
        quantity: float,
    ) -> TransferLine:
        """添加移库行。"""
        if self._status != TransferStatus.DRAFT:
            raise WMSError(
                WMSErrorCode.TRANSFER_NOT_FOUND,
                "非草稿状态不能添加移库行",
            )
        line = TransferLine(
            transfer_order_id=self._id.value,
            sku_id=sku_id,
            source_location_id=source_location_id,
            target_location_id=target_location_id,
            quantity=quantity,
        )
        self._lines.append(line)
        self._touch()
        return line

    def submit(self) -> None:
        """提交移库单（DRAFT→SUBMITTED）。"""
        if self._status != TransferStatus.DRAFT:
            raise WMSError(
                WMSErrorCode.TRANSFER_NOT_FOUND,
                "非草稿状态不能提交",
            )
        self._status = TransferStatus.SUBMITTED
        self._touch()

    def approve(self, approver_id: UUID, opinion: str = "") -> None:
        """审批通过（SUBMITTED→APPROVED）。"""
        if self._status != TransferStatus.SUBMITTED:
            raise WMSError(
                WMSErrorCode.TRANSFER_NOT_FOUND,
                "非提交状态不能审批",
            )
        self._status = TransferStatus.APPROVED
        self._approver_id = approver_id
        self._approved_at = datetime.now(timezone.utc)
        self._approval_opinion = opinion
        self._touch()

    def reject(self, approver_id: UUID, opinion: str = "") -> None:
        """审批拒绝（SUBMITTED→REJECTED）。"""
        if self._status != TransferStatus.SUBMITTED:
            raise WMSError(
                WMSErrorCode.TRANSFER_NOT_FOUND,
                "非提交状态不能审批",
            )
        self._status = TransferStatus.REJECTED
        self._approver_id = approver_id
        self._approved_at = datetime.now(timezone.utc)
        self._approval_opinion = opinion
        self._touch()

    def execute(self, idempotency_key: str | None = None) -> None:
        """执行移库（APPROVED→EXECUTING 或 SUBMITTED→EXECUTING 无需审批时）。"""
        if self._require_approval:
            if self._status != TransferStatus.APPROVED:
                raise WMSError(
                    WMSErrorCode.TRANSFER_NOT_FOUND,
                    "需审批的移库单未审批通过",
                )
        else:
            if self._status not in (TransferStatus.SUBMITTED, TransferStatus.APPROVED):
                raise WMSError(
                    WMSErrorCode.TRANSFER_NOT_FOUND,
                    "移库单未提交",
                )
        self._status = TransferStatus.EXECUTING
        self._touch()

    def complete(self) -> None:
        """完成移库。"""
        if self._status != TransferStatus.EXECUTING:
            raise WMSError(
                WMSErrorCode.TRANSFER_NOT_FOUND,
                "移库单未执行，不能完成",
            )
        self._status = TransferStatus.COMPLETED
        self._touch()