"""REL 6 个门禁校验器单元测试 - MilestoneFinalPass / CoreFreezeHash / Regression378 /
GitWorktreeClean / GitTagConflict / CertValidity。

覆盖 application/rel/gate_checkers/*.py 的每个 checker 的 gate_type、
PASS/FAIL 分支、异常处理、跳过逻辑、错误码映射。
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.application.rel.gate_checkers.cert_validity_checker import CertValidityChecker
from app.application.rel.gate_checkers.core_freeze_hash_comparator import (
    CoreFreezeHashComparator,
)
from app.application.rel.gate_checkers.git_tag_conflict_checker import (
    GitTagConflictChecker,
)
from app.application.rel.gate_checkers.git_worktree_clean_checker import (
    GitWorktreeCleanChecker,
)
from app.application.rel.gate_checkers.milestone_final_pass_checker import (
    MilestoneFinalPassChecker,
)
from app.application.rel.gate_checkers.regression_gate_runner import RegressionGateRunner
from app.domain.rel.enums import GateType
from app.domain.rel.error_codes import RELErrorCode
from app.infrastructure.rel.clients.git_client import GitClient, WorktreeStatus


_RELEASE_ID = uuid4()
_EXECUTED_BY = "alice"


# =====================================================================
# MilestoneFinalPassChecker
# =====================================================================


class MilestoneFinalPassCheckerTest:
    """MilestoneFinalPassChecker 10 里程碑 FINAL PASS 校验测试。"""

    def _expected_milestones(self) -> list[str]:
        return [
            "eitp_mt_001", "eitp_iam_001", "eitp_inv_001", "eitp_mdm_001",
            "eitp_wms_001", "eitp_pur_001", "eitp_sal_001", "eitp_sec_001",
            "eitp_plt_001", "eitp_prod_001",
        ]

    async def test_gate_type_is_milestone_final_pass(self) -> None:
        checker = MilestoneFinalPassChecker(specs_root="/tmp/specs")
        assert checker.gate_type == GateType.MILESTONE_FINAL_PASS

    async def test_all_milestones_final_pass_returns_pass(self, tmp_path) -> None:
        for ms in self._expected_milestones():
            (tmp_path / ms).mkdir(parents=True)
            (tmp_path / ms / "review.md").write_text("# Review\nFINAL PASS", encoding="utf-8")
        checker = MilestoneFinalPassChecker(specs_root=str(tmp_path))
        result = await checker.check(_RELEASE_ID, _EXECUTED_BY)
        assert result.passed is True
        assert result.error_code is None
        assert result.detail["all_final_pass"] is True
        assert result.detail["checked"] == 10

    async def test_missing_review_md_returns_fail(self, tmp_path) -> None:
        checker = MilestoneFinalPassChecker(specs_root=str(tmp_path))
        result = await checker.check(_RELEASE_ID, _EXECUTED_BY)
        assert result.passed is False
        assert result.error_code == RELErrorCode.GATE_MILESTONE_NOT_PASS.value
        assert len(result.detail["failed_milestones"]) == 10

    async def test_review_without_final_pass_returns_fail(self, tmp_path) -> None:
        for ms in self._expected_milestones():
            (tmp_path / ms).mkdir(parents=True)
            (tmp_path / ms / "review.md").write_text("# Review\nPENDING", encoding="utf-8")
        checker = MilestoneFinalPassChecker(specs_root=str(tmp_path))
        result = await checker.check(_RELEASE_ID, _EXECUTED_BY)
        assert result.passed is False
        assert result.error_code == RELErrorCode.GATE_MILESTONE_NOT_PASS.value

    async def test_partial_milestones_fail(self, tmp_path) -> None:
        milestones = self._expected_milestones()
        for ms in milestones[:5]:
            (tmp_path / ms).mkdir(parents=True)
            (tmp_path / ms / "review.md").write_text("FINAL PASS", encoding="utf-8")
        checker = MilestoneFinalPassChecker(specs_root=str(tmp_path))
        result = await checker.check(_RELEASE_ID, _EXECUTED_BY)
        assert result.passed is False
        assert len(result.detail["failed_milestones"]) == 5


# =====================================================================
# CoreFreezeHashComparator
# =====================================================================


class CoreFreezeHashComparatorTest:
    """CoreFreezeHashComparator 核心资产哈希比对测试。"""

    async def test_gate_type_is_core_freeze_hash(self) -> None:
        checker = CoreFreezeHashComparator()
        assert checker.gate_type == GateType.CORE_FREEZE_HASH

    async def test_no_guard_returns_pass_with_skip_note(self) -> None:
        checker = CoreFreezeHashComparator(core_freeze_guard=None)
        result = await checker.check(_RELEASE_ID, _EXECUTED_BY)
        assert result.passed is True
        assert "note" in result.detail

    async def test_all_hashes_match_returns_pass(self) -> None:
        guard = AsyncMock()
        guard.collect_fingerprints = AsyncMock(
            return_value={"asset_a": "hash1", "asset_b": "hash2"}
        )
        guard.get_baseline_fingerprints = AsyncMock(
            return_value={"asset_a": "hash1", "asset_b": "hash2"}
        )
        checker = CoreFreezeHashComparator(core_freeze_guard=guard)
        result = await checker.check(_RELEASE_ID, _EXECUTED_BY)
        assert result.passed is True
        assert result.detail["all_match"] is True

    async def test_hash_mismatch_returns_fail(self) -> None:
        guard = AsyncMock()
        guard.collect_fingerprints = AsyncMock(
            return_value={"asset_a": "tampered", "asset_b": "hash2"}
        )
        guard.get_baseline_fingerprints = AsyncMock(
            return_value={"asset_a": "hash1", "asset_b": "hash2"}
        )
        checker = CoreFreezeHashComparator(core_freeze_guard=guard)
        result = await checker.check(_RELEASE_ID, _EXECUTED_BY)
        assert result.passed is False
        assert result.error_code == RELErrorCode.GATE_CORE_TAMPERED.value
        assert len(result.detail["tampered_assets"]) == 1

    async def test_fingerprint_collection_exception_returns_fail(self) -> None:
        guard = AsyncMock()
        guard.collect_fingerprints = AsyncMock(side_effect=RuntimeError("boom"))
        guard.get_baseline_fingerprints = AsyncMock(return_value={})
        checker = CoreFreezeHashComparator(core_freeze_guard=guard)
        result = await checker.check(_RELEASE_ID, _EXECUTED_BY)
        assert result.passed is False
        assert result.error_code == RELErrorCode.GATE_CORE_TAMPERED.value


# =====================================================================
# RegressionGateRunner
# =====================================================================


class RegressionGateRunnerTest:
    """RegressionGateRunner 378 回归门禁测试。"""

    async def test_gate_type_is_regression_378(self) -> None:
        runner = RegressionGateRunner()
        assert runner.gate_type == GateType.REGRESSION_378

    async def test_no_runner_returns_pass_with_skip_note(self) -> None:
        runner = RegressionGateRunner(test_runner=None)
        result = await runner.check(_RELEASE_ID, _EXECUTED_BY)
        assert result.passed is True
        assert "note" in result.detail

    async def test_all_378_pass_returns_pass(self) -> None:
        test_runner = AsyncMock()
        test_runner.run_all = AsyncMock(
            return_value={"total": 378, "passed": 378, "failed": 0, "failures": []}
        )
        runner = RegressionGateRunner(test_runner=test_runner)
        result = await runner.check(_RELEASE_ID, _EXECUTED_BY)
        assert result.passed is True
        assert result.detail["total"] == 378

    async def test_failures_returns_fail(self) -> None:
        test_runner = AsyncMock()
        test_runner.run_all = AsyncMock(
            return_value={"total": 378, "passed": 377, "failed": 1, "failures": ["t1"]}
        )
        runner = RegressionGateRunner(test_runner=test_runner)
        result = await runner.check(_RELEASE_ID, _EXECUTED_BY)
        assert result.passed is False
        assert result.error_code == RELErrorCode.GATE_REGRESSION_FAILED.value

    async def test_total_below_378_returns_fail(self) -> None:
        test_runner = AsyncMock()
        test_runner.run_all = AsyncMock(
            return_value={"total": 300, "passed": 300, "failed": 0, "failures": []}
        )
        runner = RegressionGateRunner(test_runner=test_runner)
        result = await runner.check(_RELEASE_ID, _EXECUTED_BY)
        assert result.passed is False
        assert result.error_code == RELErrorCode.GATE_REGRESSION_FAILED.value

    async def test_timeout_returns_fail(self) -> None:
        test_runner = AsyncMock()
        test_runner.run_all = AsyncMock(side_effect=TimeoutError("timed out"))
        runner = RegressionGateRunner(test_runner=test_runner, timeout_seconds=10)
        result = await runner.check(_RELEASE_ID, _EXECUTED_BY)
        assert result.passed is False
        assert result.error_code == RELErrorCode.GATE_REGRESSION_FAILED.value
        assert result.detail["timeout_seconds"] == 10

    async def test_execution_exception_returns_fail(self) -> None:
        test_runner = AsyncMock()
        test_runner.run_all = AsyncMock(side_effect=RuntimeError("crash"))
        runner = RegressionGateRunner(test_runner=test_runner)
        result = await runner.check(_RELEASE_ID, _EXECUTED_BY)
        assert result.passed is False
        assert result.error_code == RELErrorCode.GATE_REGRESSION_FAILED.value


# =====================================================================
# GitWorktreeCleanChecker
# =====================================================================


class GitWorktreeCleanCheckerTest:
    """GitWorktreeCleanChecker 工作区干净校验测试。"""

    async def test_gate_type_is_git_clean(self) -> None:
        git_client = AsyncMock(spec=GitClient)
        checker = GitWorktreeCleanChecker(git_client=git_client)
        assert checker.gate_type == GateType.GIT_CLEAN

    async def test_clean_worktree_returns_pass(self) -> None:
        git_client = AsyncMock(spec=GitClient)
        git_client.check_worktree_clean = AsyncMock(
            return_value=WorktreeStatus(is_clean=True, dirty_files=[])
        )
        checker = GitWorktreeCleanChecker(git_client=git_client)
        result = await checker.check(_RELEASE_ID, _EXECUTED_BY)
        assert result.passed is True
        assert result.detail["clean"] is True

    async def test_dirty_worktree_returns_fail(self) -> None:
        git_client = AsyncMock(spec=GitClient)
        git_client.check_worktree_clean = AsyncMock(
            return_value=WorktreeStatus(is_clean=False, dirty_files=["a.py", "b.py"])
        )
        checker = GitWorktreeCleanChecker(git_client=git_client)
        result = await checker.check(_RELEASE_ID, _EXECUTED_BY)
        assert result.passed is False
        assert result.error_code == RELErrorCode.GATE_DIRTY_WORKTREE.value
        assert result.detail["dirty_files"] == ["a.py", "b.py"]


# =====================================================================
# GitTagConflictChecker
# =====================================================================


class GitTagConflictCheckerTest:
    """GitTagConflictChecker Tag 冲突校验测试。"""

    async def test_gate_type_is_tag_conflict(self) -> None:
        git_client = AsyncMock(spec=GitClient)
        checker = GitTagConflictChecker(git_client=git_client, tag_name="v1.0.0")
        assert checker.gate_type == GateType.TAG_CONFLICT

    async def test_tag_not_exists_returns_pass(self) -> None:
        git_client = AsyncMock(spec=GitClient)
        git_client.check_tag_exists = AsyncMock(return_value=False)
        checker = GitTagConflictChecker(git_client=git_client, tag_name="v1.0.0")
        result = await checker.check(_RELEASE_ID, _EXECUTED_BY)
        assert result.passed is True
        assert result.detail["exists"] is False

    async def test_tag_exists_returns_fail(self) -> None:
        git_client = AsyncMock(spec=GitClient)
        git_client.check_tag_exists = AsyncMock(return_value=True)
        checker = GitTagConflictChecker(git_client=git_client, tag_name="v1.0.0")
        result = await checker.check(_RELEASE_ID, _EXECUTED_BY)
        assert result.passed is False
        assert result.error_code == RELErrorCode.GATE_TAG_EXISTS.value
        assert result.detail["tag"] == "v1.0.0"


# =====================================================================
# CertValidityChecker
# =====================================================================


class CertValidityCheckerTest:
    """CertValidityChecker 证书与证明书有效期校验测试。"""

    async def test_gate_type_is_cert_validity(self) -> None:
        checker = CertValidityChecker()
        assert checker.gate_type == GateType.CERT_VALIDITY

    async def test_no_repos_returns_pass(self) -> None:
        checker = CertValidityChecker()
        result = await checker.check(_RELEASE_ID, _EXECUTED_BY)
        assert result.passed is True

    async def test_valid_certs_and_dossiers_return_pass(self) -> None:
        future = datetime.now(timezone.utc) + timedelta(days=30)
        sec_repo = AsyncMock()
        sec_repo.list_active_certs = AsyncMock(
            return_value=[{"cert_id": "c1", "valid_until": future, "is_signed": True}]
        )
        dossier_repo = AsyncMock()
        dossier_repo.list_active_dossiers = AsyncMock(
            return_value=[{"dossier_id": "d1", "valid_until": future, "signer": "alice"}]
        )
        checker = CertValidityChecker(
            sec_cert_repository=sec_repo, prod_dossier_repository=dossier_repo
        )
        result = await checker.check(_RELEASE_ID, _EXECUTED_BY)
        assert result.passed is True

    async def test_expired_cert_returns_fail(self) -> None:
        past = datetime.now(timezone.utc) - timedelta(days=1)
        sec_repo = AsyncMock()
        sec_repo.list_active_certs = AsyncMock(
            return_value=[{"cert_id": "c1", "valid_until": past, "is_signed": True}]
        )
        checker = CertValidityChecker(sec_cert_repository=sec_repo)
        result = await checker.check(_RELEASE_ID, _EXECUTED_BY)
        assert result.passed is False
        assert result.error_code == RELErrorCode.GATE_CERT_INVALID.value

    async def test_unsigned_cert_returns_fail(self) -> None:
        future = datetime.now(timezone.utc) + timedelta(days=30)
        sec_repo = AsyncMock()
        sec_repo.list_active_certs = AsyncMock(
            return_value=[{"cert_id": "c1", "valid_until": future, "is_signed": False}]
        )
        checker = CertValidityChecker(sec_cert_repository=sec_repo)
        result = await checker.check(_RELEASE_ID, _EXECUTED_BY)
        assert result.passed is False
        assert result.error_code == RELErrorCode.GATE_CERT_INVALID.value

    async def test_expired_dossier_returns_fail(self) -> None:
        past = datetime.now(timezone.utc) - timedelta(days=1)
        dossier_repo = AsyncMock()
        dossier_repo.list_active_dossiers = AsyncMock(
            return_value=[{"dossier_id": "d1", "valid_until": past, "signer": "alice"}]
        )
        checker = CertValidityChecker(prod_dossier_repository=dossier_repo)
        result = await checker.check(_RELEASE_ID, _EXECUTED_BY)
        assert result.passed is False
        assert result.error_code == RELErrorCode.GATE_CERT_INVALID.value

    async def test_unsigned_dossier_returns_fail(self) -> None:
        future = datetime.now(timezone.utc) + timedelta(days=30)
        dossier_repo = AsyncMock()
        dossier_repo.list_active_dossiers = AsyncMock(
            return_value=[{"dossier_id": "d1", "valid_until": future, "signer": None}]
        )
        checker = CertValidityChecker(prod_dossier_repository=dossier_repo)
        result = await checker.check(_RELEASE_ID, _EXECUTED_BY)
        assert result.passed is False
        assert result.error_code == RELErrorCode.GATE_CERT_INVALID.value

    async def test_sec_cert_query_error_returns_fail(self) -> None:
        sec_repo = AsyncMock()
        sec_repo.list_active_certs = AsyncMock(side_effect=RuntimeError("db down"))
        checker = CertValidityChecker(sec_cert_repository=sec_repo)
        result = await checker.check(_RELEASE_ID, _EXECUTED_BY)
        assert result.passed is False
        assert result.error_code == RELErrorCode.GATE_CERT_INVALID.value

    async def test_prod_dossier_query_error_returns_fail(self) -> None:
        dossier_repo = AsyncMock()
        dossier_repo.list_active_dossiers = AsyncMock(side_effect=RuntimeError("dossier db down"))
        checker = CertValidityChecker(prod_dossier_repository=dossier_repo)
        result = await checker.check(_RELEASE_ID, _EXECUTED_BY)
        assert result.passed is False
        assert result.error_code == RELErrorCode.GATE_CERT_INVALID.value
        assert any(
            i.get("type") == "prod_dossier_query_error" for i in result.detail["issues"]
        )