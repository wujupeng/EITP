"""FIN 资金调拨聚合根 - TreasuryTransferAggregate。"""

from __future__ import annotations

from dataclasses import dataclass, field, replace as dataclass_replace
from datetime import datetime, timezone
from uuid import UUID, uuid4

from app.domain.fin.error_codes import FINErrorCode
from app.domain.fin.exceptions import FINError
from app.domain.fin.value_objects.enums import TransferStatus
from app.domain.fin.value_objects.money import Money


@dataclass(frozen=True)
class TreasuryTransferAggregate:
    """资金调拨聚合根 - 状态机驱动调拨全生命周期。"""

    transfer_id: UUID
    transfer_no: str
    from_account_id: UUID
    to_account_id: UUID
    transfer_amount: Money
    reason: str
    status: TransferStatus
    approver_ids: tuple[str, ...]
    tenant_id: UUID
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @classmethod
    def create(
        cls,
        transfer_no: str,
        from_account_id: UUID,
        to_account_id: UUID,
        transfer_amount: Money,
        reason: str,
        tenant_id: UUID,
    ) -> TreasuryTransferAggregate:
        if from_account_id == to_account_id:
            raise FINError(
                FINErrorCode.TREASURY_TRANSFER_SAME_ACCOUNT,
                f"transfer {transfer_no} from and to account are the same",
            )
        return cls(
            transfer_id=uuid4(),
            transfer_no=transfer_no,
            from_account_id=from_account_id,
            to_account_id=to_account_id,
            transfer_amount=transfer_amount,
            reason=reason,
            status=TransferStatus.PENDING_APPROVAL,
            approver_ids=(),
            tenant_id=tenant_id,
        )

    def _check_transition(self, expected: TransferStatus) -> None:
        if self.status != expected:
            raise FINError(
                FINErrorCode.TREASURY_TRANSFER_INVALID_TRANSITION,
                f"transfer {self.transfer_no} invalid transition: "
                f"{self.status.value} -> expected {expected.value}",
            )

    def approve(self, approver_id: str) -> TreasuryTransferAggregate:
        self._check_transition(TransferStatus.PENDING_APPROVAL)
        new_approvers = self.approver_ids + (approver_id,)
        return dataclass_replace(
            self,
            status=TransferStatus.APPROVED,
            approver_ids=new_approvers,
            updated_at=datetime.now(timezone.utc),
        )

    def execute(self) -> TreasuryTransferAggregate:
        self._check_transition(TransferStatus.APPROVED)
        return dataclass_replace(
            self,
            status=TransferStatus.EXECUTING,
            updated_at=datetime.now(timezone.utc),
        )

    def transfer_success(self) -> TreasuryTransferAggregate:
        self._check_transition(TransferStatus.EXECUTING)
        return dataclass_replace(
            self,
            status=TransferStatus.SUCCESS,
            updated_at=datetime.now(timezone.utc),
        )

    def transfer_fail(self, reason: str) -> TreasuryTransferAggregate:
        self._check_transition(TransferStatus.EXECUTING)
        return dataclass_replace(
            self,
            status=TransferStatus.FAILED,
            updated_at=datetime.now(timezone.utc),
        )

    def cancel(self) -> TreasuryTransferAggregate:
        if self.status not in (
            TransferStatus.PENDING_APPROVAL,
            TransferStatus.FAILED,
        ):
            raise FINError(
                FINErrorCode.TREASURY_TRANSFER_INVALID_TRANSITION,
                f"transfer {self.transfer_no} cannot cancel from {self.status.value}",
            )
        return dataclass_replace(
            self,
            status=TransferStatus.CANCELLED,
            updated_at=datetime.now(timezone.utc),
        )