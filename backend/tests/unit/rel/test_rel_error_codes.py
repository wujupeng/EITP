"""REL 错误码枚举单元测试 - RELErrorCode(63) 唯一性 / EITP_REL_ 前缀 / 计数 / 分类覆盖。

覆盖 domain/rel/error_codes.py 的 RELErrorCode 全部 63 个错误码的唯一性、
前缀规范、关键分类存在性（GATE/TAG/MIGRATION/SEAL/CO_SIGN/FREEZE 等）。
"""

from __future__ import annotations

from app.domain.rel.error_codes import RELErrorCode


class RELErrorCodeTest:
    """RELErrorCode 枚举完整性测试。"""

    def test_rel_error_code_has_63_unique_values(self) -> None:
        values = [c.value for c in RELErrorCode]
        assert len(values) == 63
        assert len(values) == len(set(values)), "存在重复错误码"

    def test_all_codes_carry_eitp_rel_prefix(self) -> None:
        for code in RELErrorCode:
            assert code.value.startswith("EITP_REL_"), f"{code} 前缀不符"

    def test_code_value_equals_eitp_rel_plus_name(self) -> None:
        for code in RELErrorCode:
            assert code.value == f"EITP_REL_{code.name}"

    def test_is_str_enum(self) -> None:
        assert RELErrorCode.INTERNAL_ERROR == "EITP_REL_INTERNAL_ERROR"
        assert isinstance(RELErrorCode.INTERNAL_ERROR, str)

    def test_gate_category_codes_present(self) -> None:
        expected = {
            "EITP_REL_GATE_MILESTONE_NOT_PASS",
            "EITP_REL_GATE_CORE_TAMPERED",
            "EITP_REL_GATE_REGRESSION_FAILED",
            "EITP_REL_GATE_DIRTY_WORKTREE",
            "EITP_REL_GATE_TAG_EXISTS",
            "EITP_REL_GATE_CERT_INVALID",
            "EITP_REL_GATE_BYPASS_FORBIDDEN",
        }
        actual = {c.value for c in RELErrorCode if c.value.startswith("EITP_REL_GATE_")}
        assert expected.issubset(actual)

    def test_tag_category_codes_present(self) -> None:
        tag_codes = {c.value for c in RELErrorCode if c.value.startswith("EITP_REL_TAG_")}
        assert "EITP_REL_TAG_NOT_ANNOTATED" in tag_codes
        assert "EITP_REL_TAG_DELETE_FORBIDDEN" in tag_codes
        assert "EITP_REL_TAG_PUSH_FAILED" in tag_codes
        assert len(tag_codes) >= 7

    def test_seal_category_codes_present(self) -> None:
        seal_codes = {c.value for c in RELErrorCode if c.value.startswith("EITP_REL_SEAL_")}
        assert "EITP_REL_SEAL_NOT_CO_SIGNED" in seal_codes
        assert "EITP_REL_SEAL_INVALID_STATE_TRANSITION" in seal_codes
        assert "EITP_REL_SEAL_NOT_FOUND" in seal_codes
        assert len(seal_codes) >= 6

    def test_co_sign_category_codes_present(self) -> None:
        cosign_codes = {
            c.value for c in RELErrorCode if c.value.startswith("EITP_REL_CO_SIGN_")
        }
        assert "EITP_REL_CO_SIGN_UNAUTHORIZED_RELEASER" in cosign_codes
        assert "EITP_REL_CO_SIGN_UNAUTHORIZED_SECURITY" in cosign_codes
        assert "EITP_REL_CO_SIGN_ALREADY_SIGNED" in cosign_codes

    def test_freeze_declaration_category_codes_present(self) -> None:
        freeze_codes = {
            c.value for c in RELErrorCode if c.value.startswith("EITP_REL_FREEZE_DECLARATION_")
        }
        assert "EITP_REL_FREEZE_DECLARATION_MISSING" in freeze_codes
        assert "EITP_REL_FREEZE_DECLARATION_ALREADY_EFFECTIVE" in freeze_codes
        assert "EITP_REL_FREEZE_DECLARATION_REVOKED" in freeze_codes

    def test_asset_snapshot_category_codes_present(self) -> None:
        snapshot_codes = {
            c.value for c in RELErrorCode if c.value.startswith("EITP_REL_ASSET_SNAPSHOT_")
        }
        assert "EITP_REL_ASSET_SNAPSHOT_TAMPERED" in snapshot_codes
        assert "EITP_REL_ASSET_SNAPSHOT_NOT_FOUND" in snapshot_codes
        assert "EITP_REL_ASSET_SNAPSHOT_ARCHIVE_FAILED" in snapshot_codes

    def test_rollback_category_codes_present(self) -> None:
        rollback_codes = {
            c.value for c in RELErrorCode if c.value.startswith("EITP_REL_ROLLBACK_")
        }
        assert "EITP_REL_ROLLBACK_MIGRATION_NOT_INVERSE" in rollback_codes
        assert "EITP_REL_ROLLBACK_DRILL_FAILED" in rollback_codes
        assert "EITP_REL_ROLLBACK_PLAN_NOT_FOUND" in rollback_codes

    def test_internal_error_code_present(self) -> None:
        assert RELErrorCode.INTERNAL_ERROR.value == "EITP_REL_INTERNAL_ERROR"