"""PLT AuditRecordAggregate 单元测试 - append-only 审计记录 + 哈希链篡改检测。

覆盖 create() 工厂方法 record_hash 计算、verify_hash_chain() 正确/篡改 prev_hash、
篡改 record_hash、is_expired() 未来/过去 retention_until、genesis 哈希确定性、
3 条记录哈希链链接、frozen dataclass 不可变性。
"""

from __future__ import annotations

import os
import sys
from dataclasses import FrozenInstanceError, is_dataclass
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from app.domain.platform.audit.aggregates.audit_record_aggregate import (
    GENESIS_SEED,
    AuditRecordAggregate,
    compute_genesis_hash,
)


def _make_record(prev_hash: str, retention_until: datetime, timestamp: datetime | None = None) -> AuditRecordAggregate:
    """构造一条审计记录的辅助工厂。"""
    return AuditRecordAggregate.create(
        tenant_id=uuid4(),
        module="PLT",
        aggregate_root_type="TenantLifecycle",
        aggregate_root_id="tenant-001",
        operation_type="FREEZE",
        operator_id="admin-001",
        trace_id="trace-001",
        prev_hash=prev_hash,
        retention_until=retention_until,
        before_snapshot={"state": "ACTIVE"},
        after_snapshot={"state": "FROZEN"},
        timestamp=timestamp,
    )


class AuditRecordAggregateTest:
    """AuditRecordAggregate 哈希链与不可变性测试。"""

    def test_create_computes_correct_record_hash(self) -> None:
        # 固定 timestamp 使哈希可复算；create() 内部生成 audit_id，从实例取回再重算
        ts = datetime(2026, 9, 2, 12, 0, 0, tzinfo=timezone.utc)
        retention = ts + timedelta(days=365)
        record = _make_record(prev_hash="prev-abc", retention_until=retention, timestamp=ts)

        expected = AuditRecordAggregate._compute_hash(
            audit_id=record.audit_id,
            tenant_id=record.tenant_id,
            module=record.module,
            aggregate_root_type=record.aggregate_root_type,
            aggregate_root_id=record.aggregate_root_id,
            operation_type=record.operation_type,
            operator_id=record.operator_id,
            before_snapshot=record.before_snapshot,
            after_snapshot=record.after_snapshot,
            trace_id=record.trace_id,
            timestamp=record.timestamp,
            prev_hash=record.prev_hash,
        )
        assert record.record_hash == expected
        # record_hash 应为 64 位十六进制 SHA-256
        assert len(record.record_hash) == 64
        assert all(c in "0123456789abcdef" for c in record.record_hash)

    def test_verify_hash_chain_returns_true_for_correct_prev_hash(self) -> None:
        ts = datetime(2026, 9, 2, 12, 0, 0, tzinfo=timezone.utc)
        record = _make_record(prev_hash="prev-correct", retention_until=ts + timedelta(days=1), timestamp=ts)
        assert record.verify_hash_chain("prev-correct") is True

    def test_verify_hash_chain_returns_false_for_tampered_prev_hash(self) -> None:
        ts = datetime(2026, 9, 2, 12, 0, 0, tzinfo=timezone.utc)
        record = _make_record(prev_hash="prev-correct", retention_until=ts + timedelta(days=1), timestamp=ts)
        # 传入与 self.prev_hash 不一致的值，第二段条件 self.prev_hash == prev_record_hash 失败
        assert record.verify_hash_chain("prev-tampered") is False

    def test_verify_hash_chain_returns_false_for_tampered_record_hash(self) -> None:
        from dataclasses import replace

        ts = datetime(2026, 9, 2, 12, 0, 0, tzinfo=timezone.utc)
        record = _make_record(prev_hash="prev-correct", retention_until=ts + timedelta(days=1), timestamp=ts)
        # 篡改 record_hash：即使 prev_hash 正确，expected != tampered_record_hash
        tampered = replace(record, record_hash="0" * 64)
        assert tampered.verify_hash_chain("prev-correct") is False

    def test_is_expired_returns_false_for_future_retention(self) -> None:
        now = datetime(2026, 9, 2, 12, 0, 0, tzinfo=timezone.utc)
        record = _make_record(prev_hash="p", retention_until=now + timedelta(days=30), timestamp=now)
        assert record.is_expired(now=now) is False

    def test_is_expired_returns_true_for_past_retention(self) -> None:
        now = datetime(2026, 9, 2, 12, 0, 0, tzinfo=timezone.utc)
        record = _make_record(prev_hash="p", retention_until=now - timedelta(days=1), timestamp=now)
        assert record.is_expired(now=now) is True

    def test_genesis_hash_is_deterministic(self) -> None:
        # genesis 哈希 = SHA-256(GENESIS_SEED)，固定种子应稳定可复算
        import hashlib

        expected = hashlib.sha256(GENESIS_SEED.encode("utf-8")).hexdigest()
        assert compute_genesis_hash() == expected
        # 多次调用结果一致
        assert compute_genesis_hash() == compute_genesis_hash()
        assert len(compute_genesis_hash()) == 64

    def test_hash_chain_three_records_chain_correctly(self) -> None:
        ts = datetime(2026, 9, 2, 12, 0, 0, tzinfo=timezone.utc)
        retention = ts + timedelta(days=365)
        genesis = compute_genesis_hash()

        r1 = _make_record(prev_hash=genesis, retention_until=retention, timestamp=ts)
        r2 = _make_record(prev_hash=r1.record_hash, retention_until=retention, timestamp=ts + timedelta(seconds=1))
        r3 = _make_record(prev_hash=r2.record_hash, retention_until=retention, timestamp=ts + timedelta(seconds=2))

        # 每条记录的 prev_hash 应指向前一条的 record_hash
        assert r1.prev_hash == genesis
        assert r2.prev_hash == r1.record_hash
        assert r3.prev_hash == r2.record_hash
        # 链验证全部通过
        assert r1.verify_hash_chain(genesis) is True
        assert r2.verify_hash_chain(r1.record_hash) is True
        assert r3.verify_hash_chain(r2.record_hash) is True
        # 三条记录哈希互不相同
        assert len({r1.record_hash, r2.record_hash, r3.record_hash}) == 3

    def test_create_with_none_snapshots_uses_null_canonical_json(self) -> None:
        # before_snapshot/after_snapshot 为 None 时走 _canonical_json(None) -> "null" 分支
        ts = datetime(2026, 9, 2, 12, 0, 0, tzinfo=timezone.utc)
        record = AuditRecordAggregate.create(
            tenant_id=uuid4(),
            module="PLT",
            aggregate_root_type="X",
            aggregate_root_id="1",
            operation_type="op",
            operator_id="u",
            trace_id="t",
            prev_hash="p",
            retention_until=ts + timedelta(days=1),
            before_snapshot=None,
            after_snapshot=None,
            timestamp=ts,
        )
        # 重算应与 record_hash 一致，验证 None 分支参与哈希
        expected = AuditRecordAggregate._compute_hash(
            audit_id=record.audit_id, tenant_id=record.tenant_id, module=record.module,
            aggregate_root_type=record.aggregate_root_type, aggregate_root_id=record.aggregate_root_id,
            operation_type=record.operation_type, operator_id=record.operator_id,
            before_snapshot=None, after_snapshot=None, trace_id=record.trace_id,
            timestamp=record.timestamp, prev_hash=record.prev_hash,
        )
        assert record.record_hash == expected

    def test_frozen_dataclass_is_immutable(self) -> None:
        ts = datetime(2026, 9, 2, 12, 0, 0, tzinfo=timezone.utc)
        record = _make_record(prev_hash="p", retention_until=ts + timedelta(days=1), timestamp=ts)
        assert is_dataclass(record)
        with pytest.raises(FrozenInstanceError):
            record.module = "IAM"  # type: ignore[misc]
        with pytest.raises(FrozenInstanceError):
            record.record_hash = "tampered"  # type: ignore[misc]