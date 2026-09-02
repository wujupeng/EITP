"""CoreFreezeDeclarationAggregate 单元测试 - DRAFT→EFFECTIVE / revoke / 不可变性。

覆盖 domain/rel/aggregates/core_freeze_declaration_aggregate.py 的 create() 初始 DRAFT、
declare_effective 转换、revoke 转换、非法转换抛 RELError、
默认 dict 字段、frozen 不可变性。
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError, is_dataclass
from uuid import UUID, uuid4

import pytest

from app.domain.rel.aggregates.core_freeze_declaration_aggregate import (
    CoreFreezeDeclarationAggregate,
)
from app.domain.rel.enums import DeclarationStatus
from app.domain.rel.error_codes import RELErrorCode
from app.domain.rel.exceptions import RELError


def _make_declaration() -> CoreFreezeDeclarationAggregate:
    return CoreFreezeDeclarationAggregate.create(
        release_id=uuid4(),
        freeze_scope=["core_iam", "core_rls"],
        freeze_baseline_hash="b" * 64,
    )


class CoreFreezeDeclarationAggregateTest:
    """CoreFreezeDeclarationAggregate 冻结声明状态机测试。"""

    # --- create() ---

    def test_create_initial_status_is_draft(self) -> None:
        decl = _make_declaration()
        assert decl.declaration_status == DeclarationStatus.DRAFT

    def test_create_generates_declaration_id(self) -> None:
        decl = _make_declaration()
        assert isinstance(decl.declaration_id, UUID)

    def test_create_preserves_freeze_scope_and_baseline_hash(self) -> None:
        release_id = uuid4()
        decl = CoreFreezeDeclarationAggregate.create(
            release_id=release_id,
            freeze_scope=["a", "b"],
            freeze_baseline_hash="hash123",
        )
        assert decl.release_id == release_id
        assert decl.freeze_scope == ["a", "b"]
        assert decl.freeze_baseline_hash == "hash123"

    def test_create_defaults_optional_dicts_to_empty(self) -> None:
        decl = _make_declaration()
        assert decl.unfreeze_process_definition == {}
        assert decl.subsequent_milestone_rules == {}

    def test_create_with_optional_dicts(self) -> None:
        decl = CoreFreezeDeclarationAggregate.create(
            release_id=uuid4(),
            freeze_scope=["x"],
            freeze_baseline_hash="h",
            unfreeze_process_definition={"step": 1},
            subsequent_milestone_rules={"rule": "strict"},
        )
        assert decl.unfreeze_process_definition == {"step": 1}
        assert decl.subsequent_milestone_rules == {"rule": "strict"}

    def test_create_sets_freeze_time(self) -> None:
        decl = _make_declaration()
        assert decl.freeze_time is not None

    # --- declare_effective() ---

    def test_declare_effective_transitions_draft_to_effective(self) -> None:
        decl = _make_declaration().declare_effective()
        assert decl.declaration_status == DeclarationStatus.EFFECTIVE

    def test_declare_effective_from_effective_raises(self) -> None:
        decl = _make_declaration().declare_effective()
        with pytest.raises(RELError) as exc:
            decl.declare_effective()
        assert exc.value.code == RELErrorCode.FREEZE_DECLARATION_ALREADY_EFFECTIVE

    def test_declare_effective_from_revoked_raises(self) -> None:
        decl = _make_declaration().declare_effective().revoke()
        with pytest.raises(RELError) as exc:
            decl.declare_effective()
        assert exc.value.code == RELErrorCode.FREEZE_DECLARATION_ALREADY_EFFECTIVE

    # --- revoke() ---

    def test_revoke_transitions_effective_to_revoked(self) -> None:
        decl = _make_declaration().declare_effective().revoke()
        assert decl.declaration_status == DeclarationStatus.REVOKED

    def test_revoke_from_draft_raises(self) -> None:
        decl = _make_declaration()
        with pytest.raises(RELError) as exc:
            decl.revoke()
        assert exc.value.code == RELErrorCode.UNFREEZE_FORBIDDEN

    def test_revoke_from_revoked_raises(self) -> None:
        decl = _make_declaration().declare_effective().revoke()
        with pytest.raises(RELError) as exc:
            decl.revoke()
        assert exc.value.code == RELErrorCode.UNFREEZE_FORBIDDEN

    # --- 不可变性 ---

    def test_frozen_dataclass_is_immutable(self) -> None:
        decl = _make_declaration()
        assert is_dataclass(decl)
        with pytest.raises(FrozenInstanceError):
            decl.declaration_status = DeclarationStatus.EFFECTIVE  # type: ignore[misc]

    def test_declare_effective_returns_new_instance(self) -> None:
        decl = _make_declaration()
        effective = decl.declare_effective()
        assert decl.declaration_status == DeclarationStatus.DRAFT
        assert effective.declaration_status == DeclarationStatus.EFFECTIVE
        assert decl is not effective

    # --- 完整生命周期 ---

    def test_full_lifecycle_draft_effective_revoked(self) -> None:
        decl = _make_declaration().declare_effective().revoke()
        assert decl.declaration_status == DeclarationStatus.REVOKED