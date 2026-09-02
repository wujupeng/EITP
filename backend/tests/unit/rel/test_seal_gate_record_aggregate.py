"""SealGateRecordAggregate 单元测试 - 创建 / append-only / 不可变性。

覆盖 domain/rel/aggregates/seal_gate_record_aggregate.py 的 create() 初始态、
gate_result/gate_detail 任意值、UUID 生成、frozen 不可变性、
6 种 GateType 全覆盖。
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError, is_dataclass
from uuid import UUID, uuid4

import pytest

from app.domain.rel.aggregates.seal_gate_record_aggregate import SealGateRecordAggregate
from app.domain.rel.enums import GateType


def _make_gate(
    gate_type: GateType = GateType.GIT_CLEAN,
    gate_result: str = "PASS",
) -> SealGateRecordAggregate:
    return SealGateRecordAggregate.create(
        release_id=uuid4(),
        gate_type=gate_type,
        gate_result=gate_result,
        gate_detail={"checked": True},
        executed_by="alice",
    )


class SealGateRecordAggregateTest:
    """SealGateRecordAggregate 创建与 append-only 测试。"""

    def test_create_generates_gate_id(self) -> None:
        record = _make_gate()
        assert isinstance(record.gate_id, UUID)

    def test_create_preserves_fields(self) -> None:
        release_id = uuid4()
        record = SealGateRecordAggregate.create(
            release_id=release_id,
            gate_type=GateType.CERT_VALIDITY,
            gate_result="FAIL",
            gate_detail={"reason": "expired"},
            executed_by="bob",
        )
        assert record.release_id == release_id
        assert record.gate_type == GateType.CERT_VALIDITY
        assert record.gate_result == "FAIL"
        assert record.gate_detail == {"reason": "expired"}
        assert record.executed_by == "bob"

    def test_create_sets_gate_time(self) -> None:
        record = _make_gate()
        assert record.gate_time is not None

    def test_create_generates_unique_gate_ids(self) -> None:
        a = _make_gate()
        b = _make_gate()
        assert a.gate_id != b.gate_id

    def test_gate_result_can_be_pass_or_fail(self) -> None:
        assert _make_gate(gate_result="PASS").gate_result == "PASS"
        assert _make_gate(gate_result="FAIL").gate_result == "FAIL"

    def test_all_six_gate_types_supported(self) -> None:
        for gate_type in GateType:
            record = _make_gate(gate_type=gate_type)
            assert record.gate_type == gate_type

    def test_frozen_dataclass_is_immutable(self) -> None:
        record = _make_gate()
        assert is_dataclass(record)
        with pytest.raises(FrozenInstanceError):
            record.gate_result = "TAMPERED"  # type: ignore[misc]

    def test_no_update_or_delete_methods_exist(self) -> None:
        record = _make_gate()
        assert not hasattr(record, "update")
        assert not hasattr(record, "delete")
        assert not hasattr(record, "mark_failed")