"""审计记录聚合根 - append-only + 哈希链篡改检测。

哈希链设计：
- 首条记录 prev_hash = SHA-256("EITP_AUDIT_GENESIS")（固定种子）
- 后续记录 prev_hash = 前一条 record_hash
- record_hash = SHA-256(本条所有字段 + prev_hash)
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from uuid import UUID, uuid4

GENESIS_SEED = "EITP_AUDIT_GENESIS"


class AuditModule(str, Enum):
    MT = "MT"
    IAM = "IAM"
    INV = "INV"
    MDM = "MDM"
    WMS = "WMS"
    PUR = "PUR"
    SAL = "SAL"
    SEC = "SEC"
    PLT = "PLT"


def compute_genesis_hash() -> str:
    return hashlib.sha256(GENESIS_SEED.encode("utf-8")).hexdigest()


def _canonical_json(obj: dict | None) -> str:
    if obj is None:
        return "null"
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, default=str)


@dataclass(frozen=True)
class AuditRecordAggregate:
    """审计记录聚合根 - 不可变，哈希链保护。"""

    audit_id: UUID
    tenant_id: UUID
    module: str
    aggregate_root_type: str
    aggregate_root_id: str
    operation_type: str
    operator_id: str
    before_snapshot: dict | None
    after_snapshot: dict | None
    trace_id: str
    timestamp: datetime
    prev_hash: str
    record_hash: str
    retention_until: datetime

    @classmethod
    def create(
        cls,
        tenant_id: UUID,
        module: str,
        aggregate_root_type: str,
        aggregate_root_id: str,
        operation_type: str,
        operator_id: str,
        trace_id: str,
        prev_hash: str,
        retention_until: datetime,
        before_snapshot: dict | None = None,
        after_snapshot: dict | None = None,
        timestamp: datetime | None = None,
    ) -> AuditRecordAggregate:
        audit_id = uuid4()
        ts = timestamp or datetime.now(timezone.utc)
        record_hash = cls._compute_hash(
            audit_id=audit_id,
            tenant_id=tenant_id,
            module=module,
            aggregate_root_type=aggregate_root_type,
            aggregate_root_id=aggregate_root_id,
            operation_type=operation_type,
            operator_id=operator_id,
            before_snapshot=before_snapshot,
            after_snapshot=after_snapshot,
            trace_id=trace_id,
            timestamp=ts,
            prev_hash=prev_hash,
        )
        return cls(
            audit_id=audit_id,
            tenant_id=tenant_id,
            module=module,
            aggregate_root_type=aggregate_root_type,
            aggregate_root_id=aggregate_root_id,
            operation_type=operation_type,
            operator_id=operator_id,
            before_snapshot=before_snapshot,
            after_snapshot=after_snapshot,
            trace_id=trace_id,
            timestamp=ts,
            prev_hash=prev_hash,
            record_hash=record_hash,
            retention_until=retention_until,
        )

    @staticmethod
    def _compute_hash(
        audit_id: UUID,
        tenant_id: UUID,
        module: str,
        aggregate_root_type: str,
        aggregate_root_id: str,
        operation_type: str,
        operator_id: str,
        before_snapshot: dict | None,
        after_snapshot: dict | None,
        trace_id: str,
        timestamp: datetime,
        prev_hash: str,
    ) -> str:
        payload = "|".join([
            str(audit_id),
            str(tenant_id),
            module,
            aggregate_root_type,
            aggregate_root_id,
            operation_type,
            operator_id,
            _canonical_json(before_snapshot),
            _canonical_json(after_snapshot),
            trace_id,
            timestamp.isoformat(),
            prev_hash,
        ])
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def verify_hash_chain(self, prev_record_hash: str) -> bool:
        expected_hash = self._compute_hash(
            audit_id=self.audit_id,
            tenant_id=self.tenant_id,
            module=self.module,
            aggregate_root_type=self.aggregate_root_type,
            aggregate_root_id=self.aggregate_root_id,
            operation_type=self.operation_type,
            operator_id=self.operator_id,
            before_snapshot=self.before_snapshot,
            after_snapshot=self.after_snapshot,
            trace_id=self.trace_id,
            timestamp=self.timestamp,
            prev_hash=prev_record_hash,
        )
        return expected_hash == self.record_hash and self.prev_hash == prev_record_hash

    def is_expired(self, now: datetime | None = None) -> bool:
        check_time = now or datetime.now(timezone.utc)
        return check_time > self.retention_until