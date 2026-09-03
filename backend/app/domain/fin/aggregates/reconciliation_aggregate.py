"""FIN 对账聚合根 - ReconciliationAggregate + ReconciliationLine + ReconciliationDifference + ReconDiffHandleRecord。"""

from __future__ import annotations

from dataclasses import dataclass, field, replace as dataclass_replace
from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import UUID, uuid4

from app.domain.fin.error_codes import FINErrorCode
from app.domain.fin.exceptions import FINError
from app.domain.fin.value_objects.enums import (
    DifferenceType,
    HandleStatus,
    ReconciliationStatus,
)
from app.domain.fin.value_objects.money import Money


@dataclass(frozen=True)
class ReconciliationLine:
    """对账明细行 - 系统侧与外部侧单据。"""

    line_no: int
    business_ref_type: str
    business_ref_id: str
    system_amount: Money
    external_amount: Money
    is_matched: bool


@dataclass(frozen=True)
class ReconciliationDifference:
    """对账差异 - 金额/时间/缺失/重复。"""

    diff_id: UUID
    line_no: int
    business_ref_type: str
    business_ref_id: str
    diff_type: DifferenceType
    diff_amount: Money
    handle_status: HandleStatus


@dataclass(frozen=True)
class ReconDiffHandleRecord:
    """差异处理记录 - append-only 不可变。"""

    record_id: UUID
    diff_id: UUID
    handle_action: str
    handler_id: str
    handle_opinion: str
    handled_at: datetime


@dataclass(frozen=True)
class ReconciliationAggregate:
    """对账聚合根 - 状态机 + 差异处理 append-only。"""

    recon_id: UUID
    recon_no: str
    period_start: date
    period_end: date
    scope_type: str
    scope_value: str
    data_source: str
    status: ReconciliationStatus
    system_amount: Money
    external_amount: Money
    matched_count: int
    diff_count: int
    lines: tuple[ReconciliationLine, ...]
    differences: tuple[ReconciliationDifference, ...]
    handle_records: tuple[ReconDiffHandleRecord, ...]
    tenant_id: UUID
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @classmethod
    def create(
        cls,
        recon_no: str,
        period_start: date,
        period_end: date,
        scope_type: str,
        scope_value: str,
        data_source: str,
        currency: str,
        tenant_id: UUID,
        lines: list[ReconciliationLine] | tuple[ReconciliationLine, ...] = (),
    ) -> ReconciliationAggregate:
        line_tuple = tuple(lines)
        system_total = Money.zero(currency)
        external_total = Money.zero(currency)
        matched = 0
        for ln in line_tuple:
            system_total = system_total.add(ln.system_amount)
            external_total = external_total.add(ln.external_amount)
            if ln.is_matched:
                matched += 1
        diff_count = len(line_tuple) - matched
        return cls(
            recon_id=uuid4(),
            recon_no=recon_no,
            period_start=period_start,
            period_end=period_end,
            scope_type=scope_type,
            scope_value=scope_value,
            data_source=data_source,
            status=ReconciliationStatus.CREATED,
            system_amount=system_total,
            external_amount=external_total,
            matched_count=matched,
            diff_count=diff_count,
            lines=line_tuple,
            differences=(),
            handle_records=(),
            tenant_id=tenant_id,
        )

    def _check_transition(self, expected: ReconciliationStatus) -> None:
        if self.status != expected:
            raise FINError(
                FINErrorCode.RECON_INVALID_TRANSITION,
                f"reconciliation {self.recon_no} invalid transition: "
                f"{self.status.value} -> expected {expected.value}",
            )

    def start_matching(self) -> ReconciliationAggregate:
        self._check_transition(ReconciliationStatus.CREATED)
        return dataclass_replace(
            self,
            status=ReconciliationStatus.MATCHING,
            updated_at=datetime.now(timezone.utc),
        )

    def finish_matching(
        self, differences: list[ReconciliationDifference]
    ) -> ReconciliationAggregate:
        self._check_transition(ReconciliationStatus.MATCHING)
        return dataclass_replace(
            self,
            status=ReconciliationStatus.MATCHED,
            differences=tuple(differences),
            diff_count=len(differences),
            updated_at=datetime.now(timezone.utc),
        )

    def handle_diff(
        self,
        diff_id: UUID,
        handle_action: str,
        handler_id: str,
        handle_opinion: str,
    ) -> ReconciliationAggregate:
        if self.status not in (
            ReconciliationStatus.MATCHED,
            ReconciliationStatus.DIFF_HANDLING,
        ):
            raise FINError(
                FINErrorCode.RECON_INVALID_TRANSITION,
                f"reconciliation {self.recon_no} cannot handle diff from {self.status.value}",
            )
        target_diff: ReconciliationDifference | None = None
        for d in self.differences:
            if d.diff_id == diff_id:
                target_diff = d
                break
        if target_diff is None:
            raise FINError(
                FINErrorCode.RECON_DIFF_NOT_FOUND,
                f"diff {diff_id} not found in reconciliation {self.recon_no}",
            )
        if target_diff.handle_status != HandleStatus.PENDING:
            raise FINError(
                FINErrorCode.RECON_DIFF_ALREADY_HANDLED,
                f"diff {diff_id} already handled with status {target_diff.handle_status.value}",
            )
        record = ReconDiffHandleRecord(
            record_id=uuid4(),
            diff_id=diff_id,
            handle_action=handle_action,
            handler_id=handler_id,
            handle_opinion=handle_opinion,
            handled_at=datetime.now(timezone.utc),
        )
        new_handle_status = HandleStatus.WRITE_OFF if handle_action == "WRITE_OFF" else HandleStatus.HANG
        new_diff = dataclass_replace(
            target_diff, handle_status=new_handle_status
        )
        new_differences = tuple(
            new_diff if d.diff_id == diff_id else d for d in self.differences
        )
        new_records = self.handle_records + (record,)
        return dataclass_replace(
            self,
            status=ReconciliationStatus.DIFF_HANDLING,
            differences=new_differences,
            handle_records=new_records,
            updated_at=datetime.now(timezone.utc),
        )

    def complete(self) -> ReconciliationAggregate:
        if self.status != ReconciliationStatus.DIFF_HANDLING:
            raise FINError(
                FINErrorCode.RECON_INVALID_TRANSITION,
                f"reconciliation {self.recon_no} cannot complete from {self.status.value}",
            )
        pending = [d for d in self.differences if d.handle_status == HandleStatus.PENDING]
        if pending:
            raise FINError(
                FINErrorCode.RECON_DIFF_ALREADY_HANDLED,
                f"reconciliation {self.recon_no} has {len(pending)} pending diffs",
            )
        return dataclass_replace(
            self,
            status=ReconciliationStatus.COMPLETED,
            updated_at=datetime.now(timezone.utc),
        )

    def fail(self, reason: str) -> ReconciliationAggregate:
        if self.status not in (
            ReconciliationStatus.MATCHING,
            ReconciliationStatus.DIFF_HANDLING,
        ):
            raise FINError(
                FINErrorCode.RECON_INVALID_TRANSITION,
                f"reconciliation {self.recon_no} cannot fail from {self.status.value}",
            )
        return dataclass_replace(
            self,
            status=ReconciliationStatus.FAILED,
            updated_at=datetime.now(timezone.utc),
        )