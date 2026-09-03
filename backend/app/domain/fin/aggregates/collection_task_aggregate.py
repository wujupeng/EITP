"""FIN 催收任务聚合根 - CollectionTaskAggregate + CollectionRecord。"""

from __future__ import annotations

from dataclasses import dataclass, field, replace as dataclass_replace
from datetime import datetime, timezone
from uuid import UUID, uuid4

from app.domain.fin.error_codes import FINErrorCode
from app.domain.fin.exceptions import FINError
from app.domain.fin.value_objects.enums import (
    CollectionStage,
    CollectionTaskStatus,
)
from app.domain.fin.value_objects.money import Money


@dataclass(frozen=True)
class CollectionRecord:
    """催收记录 - append-only 不可变。"""

    record_id: UUID
    stage: CollectionStage
    handler_id: str
    content: str
    created_at: datetime


@dataclass(frozen=True)
class CollectionTaskAggregate:
    """催收任务聚合根 - 跟踪逾期应收与催收阶段。"""

    task_id: UUID
    ar_voucher_no: str
    overdue_amount: Money
    overdue_days: int
    collection_stage: CollectionStage
    status: CollectionTaskStatus
    records: tuple[CollectionRecord, ...]
    tenant_id: UUID
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @classmethod
    def create(
        cls,
        ar_voucher_no: str,
        overdue_amount: Money,
        overdue_days: int,
        tenant_id: UUID,
    ) -> CollectionTaskAggregate:
        stage = CollectionStage.REMINDER
        if overdue_days > 90:
            stage = CollectionStage.LEGAL
        elif overdue_days > 30:
            stage = CollectionStage.URGENT
        return cls(
            task_id=uuid4(),
            ar_voucher_no=ar_voucher_no,
            overdue_amount=overdue_amount,
            overdue_days=overdue_days,
            collection_stage=stage,
            status=CollectionTaskStatus.PENDING,
            records=(),
            tenant_id=tenant_id,
        )

    def handle(
        self,
        handler_id: str,
        content: str,
        stage: CollectionStage | None = None,
    ) -> CollectionTaskAggregate:
        if self.status == CollectionTaskStatus.RESOLVED:
            raise FINError(
                FINErrorCode.COLLECTION_TASK_ALREADY_RESOLVED,
                f"collection task {self.task_id} already resolved",
            )
        record = CollectionRecord(
            record_id=uuid4(),
            stage=stage or self.collection_stage,
            handler_id=handler_id,
            content=content,
            created_at=datetime.now(timezone.utc),
        )
        new_records = self.records + (record,)
        new_status = CollectionTaskStatus.IN_PROGRESS
        return dataclass_replace(
            self,
            records=new_records,
            status=new_status,
            collection_stage=stage or self.collection_stage,
            updated_at=datetime.now(timezone.utc),
        )

    def escalate(self, handler_id: str, content: str) -> CollectionTaskAggregate:
        if self.status == CollectionTaskStatus.RESOLVED:
            raise FINError(
                FINErrorCode.COLLECTION_TASK_ALREADY_RESOLVED,
                f"collection task {self.task_id} already resolved",
            )
        record = CollectionRecord(
            record_id=uuid4(),
            stage=CollectionStage.LEGAL,
            handler_id=handler_id,
            content=content,
            created_at=datetime.now(timezone.utc),
        )
        new_records = self.records + (record,)
        return dataclass_replace(
            self,
            records=new_records,
            status=CollectionTaskStatus.ESCALATED,
            collection_stage=CollectionStage.LEGAL,
            updated_at=datetime.now(timezone.utc),
        )

    def resolve(self, handler_id: str, content: str) -> CollectionTaskAggregate:
        if self.status == CollectionTaskStatus.RESOLVED:
            raise FINError(
                FINErrorCode.COLLECTION_TASK_ALREADY_RESOLVED,
                f"collection task {self.task_id} already resolved",
            )
        record = CollectionRecord(
            record_id=uuid4(),
            stage=self.collection_stage,
            handler_id=handler_id,
            content=content,
            created_at=datetime.now(timezone.utc),
        )
        new_records = self.records + (record,)
        return dataclass_replace(
            self,
            records=new_records,
            status=CollectionTaskStatus.RESOLVED,
            updated_at=datetime.now(timezone.utc),
        )