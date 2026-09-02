"""PLT IdempotencyRecordAggregate 单元测试 - 全平台统一幂等键。

覆盖 build_idempotency_key() 格式 eitp:{tenant_id}:idem:{key}、create() 计算幂等键、
is_expired() 未来/过去、matches_request() 匹配/不匹配。
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from app.domain.platform.idempotency.aggregates.idempotency_record_aggregate import (
    IDEMPOTENCY_KEY_PREFIX,
    IDEMPOTENCY_KEY_SEGMENT,
    IdempotencyRecordAggregate,
    build_idempotency_key,
    compute_request_hash,
)


class BuildIdempotencyKeyTest:
    """build_idempotency_key 格式测试。"""

    def test_produces_expected_format_with_uuid_tenant(self) -> None:
        tenant_id = uuid4()
        key = build_idempotency_key(tenant_id, "order-create-001")
        assert key == f"eitp:{tenant_id}:idem:order-create-001"

    def test_produces_expected_format_with_str_tenant(self) -> None:
        key = build_idempotency_key("tenant-abc", "op-123")
        assert key == "eitp:tenant-abc:idem:op-123"

    def test_uses_module_prefix_and_segment_constants(self) -> None:
        assert IDEMPOTENCY_KEY_PREFIX == "eitp"
        assert IDEMPOTENCY_KEY_SEGMENT == "idem"
        key = build_idempotency_key("t", "k")
        assert key.startswith(f"{IDEMPOTENCY_KEY_PREFIX}:")
        assert f":{IDEMPOTENCY_KEY_SEGMENT}:" in key


class IdempotencyRecordAggregateTest:
    """IdempotencyRecordAggregate 幂等记录测试。"""

    def test_create_computes_correct_idempotency_key(self) -> None:
        tenant_id = uuid4()
        record = IdempotencyRecordAggregate.create(
            tenant_id=tenant_id,
            key="order-create-001",
            request_hash="abc123",
            response_cache={"status": "ok"},
            response_status=200,
            trace_id="trace-001",
        )
        assert record.idempotency_key == f"eitp:{tenant_id}:idem:order-create-001"
        assert record.request_hash == "abc123"
        assert record.response_status == 200
        assert record.tenant_id == tenant_id

    def test_create_expires_at_is_created_plus_ttl(self) -> None:
        tenant_id = uuid4()
        record = IdempotencyRecordAggregate.create(
            tenant_id=tenant_id,
            key="k",
            request_hash="h",
            response_cache={},
            response_status=201,
            trace_id="t",
            ttl_seconds=3600,
        )
        delta = record.expires_at - record.created_at
        assert timedelta(seconds=3599) < delta <= timedelta(seconds=3600)

    def test_is_expired_returns_false_for_future_expires(self) -> None:
        now = datetime(2026, 9, 2, 12, 0, 0, tzinfo=timezone.utc)
        tenant_id = uuid4()
        record = IdempotencyRecordAggregate(
            idempotency_key=build_idempotency_key(tenant_id, "k"),
            tenant_id=tenant_id,
            request_hash="h",
            response_cache={},
            response_status=200,
            trace_id="t",
            created_at=now,
            expires_at=now + timedelta(hours=1),
        )
        assert record.is_expired(now=now) is False

    def test_is_expired_returns_true_for_past_expires(self) -> None:
        now = datetime(2026, 9, 2, 12, 0, 0, tzinfo=timezone.utc)
        tenant_id = uuid4()
        record = IdempotencyRecordAggregate(
            idempotency_key=build_idempotency_key(tenant_id, "k"),
            tenant_id=tenant_id,
            request_hash="h",
            response_cache={},
            response_status=200,
            trace_id="t",
            created_at=now - timedelta(hours=2),
            expires_at=now - timedelta(hours=1),
        )
        assert record.is_expired(now=now) is True

    def test_matches_request_returns_true_for_matching_hash(self) -> None:
        body = b'{"order_id":"o-1"}'
        request_hash = compute_request_hash(body)
        tenant_id = uuid4()
        record = IdempotencyRecordAggregate.create(
            tenant_id=tenant_id,
            key="k",
            request_hash=request_hash,
            response_cache={},
            response_status=200,
            trace_id="t",
        )
        assert record.matches_request(request_hash) is True

    def test_matches_request_returns_false_for_different_hash(self) -> None:
        tenant_id = uuid4()
        record = IdempotencyRecordAggregate.create(
            tenant_id=tenant_id,
            key="k",
            request_hash="hash-a",
            response_cache={},
            response_status=200,
            trace_id="t",
        )
        assert record.matches_request("hash-b") is False

    def test_compute_request_hash_is_sha256_hex(self) -> None:
        import hashlib

        body = b"payload"
        assert compute_request_hash(body) == hashlib.sha256(body).hexdigest()
        assert len(compute_request_hash(body)) == 64