"""REL 枚举与状态机单元测试 - SealStatus 9 状态机 / AssetType 15 / GateType 6 /
DeclarationStatus / DrillStatus / VerificationStatus / SealVerdict +
is_terminal / is_valid_transition 转换矩阵全覆盖。

覆盖 domain/rel/enums.py 的全部枚举值计数、str-Enum 取值、终态判定、
合法转换矩阵与非法转换拒绝。
"""

from __future__ import annotations

import pytest

from app.domain.rel.enums import (
    AssetType,
    DeclarationStatus,
    DrillStatus,
    GateType,
    SealStatus,
    SealVerdict,
    VerificationStatus,
    is_terminal,
    is_valid_transition,
)


class SealStatusEnumTest:
    """SealStatus 9 状态枚举完整性测试。"""

    def test_seal_status_has_nine_members(self) -> None:
        assert len(list(SealStatus)) == 9

    def test_seal_status_values_are_uppercase_strings(self) -> None:
        for s in SealStatus:
            assert s.value == s.name
            assert s.value.isupper()

    def test_seal_status_is_str_enum(self) -> None:
        assert SealStatus.SEALED == "SEALED"
        assert isinstance(SealStatus.SEALED, str)

    def test_all_nine_expected_states_present(self) -> None:
        expected = {
            "REQUESTED", "GATE_RUNNING", "GATE_FAILED", "SNAPSHOT_COLLECTING",
            "SNAPSHOT_FAILED", "REPORT_ASSEMBLING", "PENDING_CO_SIGN",
            "SEALED", "FAILED",
        }
        assert {s.value for s in SealStatus} == expected


class SealVerdictEnumTest:
    """SealVerdict 最终裁决枚举测试。"""

    def test_seal_verdict_has_two_members(self) -> None:
        assert len(list(SealVerdict)) == 2

    def test_seal_verdict_values(self) -> None:
        assert SealVerdict.FINAL_PASS.value == "FINAL_PASS"
        assert SealVerdict.FINAL_FAIL.value == "FINAL_FAIL"


class AssetTypeEnumTest:
    """AssetType 15 资产类型枚举测试。"""

    def test_asset_type_has_fifteen_members(self) -> None:
        assert len(list(AssetType)) == 15

    def test_asset_type_all_values_unique(self) -> None:
        values = [a.value for a in AssetType]
        assert len(values) == len(set(values))

    def test_asset_type_expected_members_present(self) -> None:
        expected = {
            "GIT_TAG", "MIGRATION_BASELINE", "DDL_SNAPSHOT", "OPENAPI",
            "PERMISSION_MATRIX", "RLS_BASELINE", "SEC_CERT", "PROD_DOSSIER",
            "TEST_RESULT", "PERF_CAPACITY_BASELINE", "DOCKER_IMAGE_LOCK",
            "CONFIG_BASELINE", "BACKUP_EVIDENCE", "DR_EVIDENCE", "ROLLBACK_PLAN",
        }
        assert {a.value for a in AssetType} == expected

    def test_asset_type_is_str_enum(self) -> None:
        assert AssetType.GIT_TAG == "GIT_TAG"
        assert isinstance(AssetType.GIT_TAG, str)


class GateTypeEnumTest:
    """GateType 6 门禁类型枚举测试。"""

    def test_gate_type_has_six_members(self) -> None:
        assert len(list(GateType)) == 6

    def test_gate_type_expected_members_present(self) -> None:
        expected = {
            "MILESTONE_FINAL_PASS", "CORE_FREEZE_HASH", "REGRESSION_378",
            "GIT_CLEAN", "TAG_CONFLICT", "CERT_VALIDITY",
        }
        assert {g.value for g in GateType} == expected

    def test_gate_type_all_values_unique(self) -> None:
        values = [g.value for g in GateType]
        assert len(values) == len(set(values))


class DeclarationStatusEnumTest:
    """DeclarationStatus 冻结声明状态枚举测试。"""

    def test_declaration_status_has_three_members(self) -> None:
        assert len(list(DeclarationStatus)) == 3

    def test_declaration_status_values(self) -> None:
        assert DeclarationStatus.DRAFT.value == "DRAFT"
        assert DeclarationStatus.EFFECTIVE.value == "EFFECTIVE"
        assert DeclarationStatus.REVOKED.value == "REVOKED"


class DrillStatusEnumTest:
    """DrillStatus 演练状态枚举测试。"""

    def test_drill_status_has_three_members(self) -> None:
        assert len(list(DrillStatus)) == 3

    def test_drill_status_values(self) -> None:
        assert DrillStatus.NOT_DRILLED.value == "NOT_DRILLED"
        assert DrillStatus.DRILLED_PASS.value == "DRILLED_PASS"
        assert DrillStatus.DRILLED_FAIL.value == "DRILLED_FAIL"


class VerificationStatusEnumTest:
    """VerificationStatus 资产校验状态枚举测试。"""

    def test_verification_status_has_two_members(self) -> None:
        assert len(list(VerificationStatus)) == 2

    def test_verification_status_values(self) -> None:
        assert VerificationStatus.VERIFIED.value == "VERIFIED"
        assert VerificationStatus.TAMPERED.value == "TAMPERED"


class IsTerminalFunctionTest:
    """is_terminal 终态判定函数测试。"""

    @pytest.mark.parametrize(
        "status",
        [
            SealStatus.SEALED,
            SealStatus.GATE_FAILED,
            SealStatus.SNAPSHOT_FAILED,
            SealStatus.FAILED,
        ],
    )
    def test_terminal_states_return_true(self, status: SealStatus) -> None:
        assert is_terminal(status) is True

    @pytest.mark.parametrize(
        "status",
        [
            SealStatus.REQUESTED,
            SealStatus.GATE_RUNNING,
            SealStatus.SNAPSHOT_COLLECTING,
            SealStatus.REPORT_ASSEMBLING,
            SealStatus.PENDING_CO_SIGN,
        ],
    )
    def test_non_terminal_states_return_false(self, status: SealStatus) -> None:
        assert is_terminal(status) is False

    def test_exactly_four_terminal_states(self) -> None:
        terminals = [s for s in SealStatus if is_terminal(s)]
        assert len(terminals) == 4


class IsValidTransitionFunctionTest:
    """is_valid_transition 状态机转换矩阵测试。"""

    @pytest.mark.parametrize(
        "current,target",
        [
            (SealStatus.REQUESTED, SealStatus.GATE_RUNNING),
            (SealStatus.REQUESTED, SealStatus.FAILED),
            (SealStatus.GATE_RUNNING, SealStatus.SNAPSHOT_COLLECTING),
            (SealStatus.GATE_RUNNING, SealStatus.GATE_FAILED),
            (SealStatus.SNAPSHOT_COLLECTING, SealStatus.REPORT_ASSEMBLING),
            (SealStatus.SNAPSHOT_COLLECTING, SealStatus.SNAPSHOT_FAILED),
            (SealStatus.REPORT_ASSEMBLING, SealStatus.PENDING_CO_SIGN),
            (SealStatus.REPORT_ASSEMBLING, SealStatus.FAILED),
            (SealStatus.PENDING_CO_SIGN, SealStatus.SEALED),
            (SealStatus.PENDING_CO_SIGN, SealStatus.FAILED),
        ],
    )
    def test_valid_transitions_return_true(
        self, current: SealStatus, target: SealStatus
    ) -> None:
        assert is_valid_transition(current, target) is True

    @pytest.mark.parametrize(
        "current,target",
        [
            # 反向/跳跃转换非法
            (SealStatus.REQUESTED, SealStatus.SEALED),
            (SealStatus.REQUESTED, SealStatus.PENDING_CO_SIGN),
            (SealStatus.GATE_RUNNING, SealStatus.SEALED),
            (SealStatus.GATE_RUNNING, SealStatus.REQUESTED),
            (SealStatus.SNAPSHOT_COLLECTING, SealStatus.SEALED),
            (SealStatus.REPORT_ASSEMBLING, SealStatus.GATE_RUNNING),
            (SealStatus.PENDING_CO_SIGN, SealStatus.GATE_RUNNING),
            (SealStatus.PENDING_CO_SIGN, SealStatus.REQUESTED),
        ],
    )
    def test_invalid_transitions_return_false(
        self, current: SealStatus, target: SealStatus
    ) -> None:
        assert is_valid_transition(current, target) is False

    @pytest.mark.parametrize(
        "status",
        [
            SealStatus.SEALED,
            SealStatus.GATE_FAILED,
            SealStatus.SNAPSHOT_FAILED,
            SealStatus.FAILED,
        ],
    )
    def test_terminal_states_have_no_outgoing_transitions(self, status: SealStatus) -> None:
        for target in SealStatus:
            assert is_valid_transition(status, target) is False

    def test_request_to_gate_running_is_valid(self) -> None:
        assert is_valid_transition(SealStatus.REQUESTED, SealStatus.GATE_RUNNING) is True

    def test_sealed_to_anything_is_invalid(self) -> None:
        for target in SealStatus:
            assert is_valid_transition(SealStatus.SEALED, target) is False