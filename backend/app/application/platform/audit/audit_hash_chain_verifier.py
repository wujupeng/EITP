"""审计哈希链校验器 - 篡改检测 + 告警。"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from structlog import get_logger

from app.domain.platform.audit.aggregates.audit_record_aggregate import (
    AuditRecordAggregate,
    compute_genesis_hash,
)
from app.domain.platform.error_codes import PLTErrorCode
from app.domain.platform.exceptions import PLTError

logger = get_logger(__name__)


class AuditHashChainVerifier:
    """审计哈希链校验器 - 遍历记录校验 record_hash 一致性。"""

    def __init__(self, repository: Any | None = None) -> None:
        self._repository = repository

    def verify_chain(self, records: list[dict]) -> tuple[bool, list[int]]:
        """校验记录列表的哈希链完整性，返回 (是否通过, 篡改位置列表)。"""
        tampered_positions: list[int] = []
        prev_hash = compute_genesis_hash()

        for i, row in enumerate(records):
            expected_prev = prev_hash
            actual_prev = row.get("prev_hash", "")
            if actual_prev != expected_prev:
                tampered_positions.append(i)
                logger.error(
                    "audit_hash_chain_broken",
                    position=i,
                    expected_prev=expected_prev,
                    actual_prev=actual_prev,
                )
                prev_hash = row.get("record_hash", "")
                continue

            record = AuditRecordAggregate(
                audit_id=row["audit_id"],
                tenant_id=row["tenant_id"],
                module=row["module"],
                aggregate_root_type=row["aggregate_root_type"],
                aggregate_root_id=row["aggregate_root_id"],
                operation_type=row["operation_type"],
                operator_id=row["operator_id"],
                before_snapshot=row.get("before_snapshot"),
                after_snapshot=row.get("after_snapshot"),
                trace_id=row["trace_id"],
                timestamp=row["timestamp"],
                prev_hash=row["prev_hash"],
                record_hash=row["record_hash"],
                retention_until=row["retention_until"],
            )

            if not record.verify_hash_chain(prev_hash):
                tampered_positions.append(i)
                logger.error(
                    "audit_tamper_detected",
                    position=i,
                    audit_id=str(row["audit_id"]),
                )

            prev_hash = row.get("record_hash", "")

        return len(tampered_positions) == 0, tampered_positions

    async def verify_tenant(self, tenant_id: UUID) -> tuple[bool, list[int]]:
        if self._repository is None:
            raise PLTError(PLTErrorCode.INTERNAL_ERROR, "仓储未注入")
        records = await self._repository.get_chain_for_tenant(tenant_id)
        return self.verify_chain(records)

    def raise_if_tampered(self, tampered_positions: list[int]) -> None:
        if tampered_positions:
            raise PLTError(
                PLTErrorCode.AUDIT_TAMPER_DETECTED,
                f"审计哈希链篡改检测失败，篡改位置: {tampered_positions}",
                {"tampered_positions": tampered_positions},
            )