"""EITP-SEC-001 认证聚合根单元测试。

覆盖:
- CertificationBatchAggregate: start/complete/fail 状态机
- CertificationItemAggregate: PENDING→EXECUTING→PASS/FAIL/UNEXECUTABLE 三态机
- CertificationReportAggregate: JSON/HTML 双格式渲染
- CertificationCertificateAggregate: HMAC-SHA256 sign/verify/revoke
- CertificationConfigAggregate: 配置更新与跳过
- CertificationAuditAggregate: append-only 与篡改检测
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from app.domain.sec.certification.aggregates.certification_audit_aggregate import (
    CertificationAuditAggregate,
)
from app.domain.sec.certification.aggregates.certification_batch_aggregate import (
    CertificationBatchAggregate,
)
from app.domain.sec.certification.aggregates.certification_certificate_aggregate import (
    CertificationCertificateAggregate,
)
from app.domain.sec.certification.aggregates.certification_config_aggregate import (
    CertificationConfigAggregate,
)
from app.domain.sec.certification.aggregates.certification_item_aggregate import (
    CertificationItemAggregate,
)
from app.domain.sec.certification.aggregates.certification_report_aggregate import (
    CertificationReportAggregate,
)
from app.domain.sec.certification.value_objects.audit_action_type import AuditActionType
from app.domain.sec.certification.value_objects.batch_status import BatchStatus
from app.domain.sec.certification.value_objects.cert_status import CertStatus
from app.domain.sec.certification.value_objects.evidence_snapshot import EvidenceSnapshot
from app.domain.sec.certification.value_objects.isolation_layer import (
    Conclusion,
    IsolationLayer,
    NineOperation,
)
from app.interfaces.middleware.error_handler import SECError, SECErrorCode


def _full_evidence() -> EvidenceSnapshot:
    return EvidenceSnapshot(
        request_log={"method": "GET", "path": "/api/v1/inv/products"},
        response_log={"status": 200, "body": "ok"},
        sql_plan="SeqScan",
        rls_hits=[{"tenant_id": "t1"}],
        redis_keys=["eitp:t1:inv:1"],
        audit_records=[{"action": "select"}],
    )


class CertificationBatchAggregateTest:
    """CertificationBatchAggregate 批次状态机。"""

    def test_start_transitions_pending_to_running(self) -> None:
        batch = CertificationBatchAggregate()
        assert batch.status == BatchStatus.PENDING
        batch.start()
        assert batch.status == BatchStatus.RUNNING
        assert batch.started_at is not None

    def test_start_when_not_pending_raises(self) -> None:
        batch = CertificationBatchAggregate()
        batch.start()
        with pytest.raises(SECError) as exc:
            batch.start()
        assert exc.value.code == SECErrorCode.CERT_ALREADY_RUNNING

    def test_complete_transitions_running_to_completed(self) -> None:
        batch = CertificationBatchAggregate()
        batch.start()
        batch.complete(passed=500, failed=10, unexecutable=14)
        assert batch.status == BatchStatus.COMPLETED
        assert batch.passed_count == 500
        assert batch.failed_count == 10
        assert batch.unexecutable_count == 14
        assert batch.total_items == 524
        assert batch.completed_at is not None

    def test_complete_when_not_running_raises(self) -> None:
        batch = CertificationBatchAggregate()
        with pytest.raises(SECError) as exc:
            batch.complete(1, 0, 0)
        assert exc.value.code == SECErrorCode.CERT_ISSUE_FAILED

    def test_fail_transitions_to_failed(self) -> None:
        batch = CertificationBatchAggregate()
        batch.start()
        batch.fail("infra unreachable")
        assert batch.status == BatchStatus.FAILED
        assert batch.completed_at is not None

    def test_pass_rate_calculation(self) -> None:
        batch = CertificationBatchAggregate()
        batch.start()
        batch.complete(passed=400, failed=100, unexecutable=24)
        assert batch.pass_rate == pytest.approx(400 / 524)

    def test_pass_rate_zero_when_no_items(self) -> None:
        batch = CertificationBatchAggregate()
        assert batch.pass_rate == 0.0

    def test_all_passed_true_only_when_completed_no_failures(self) -> None:
        batch = CertificationBatchAggregate()
        batch.start()
        batch.complete(passed=524, failed=0, unexecutable=0)
        assert batch.all_passed is True

    def test_all_passed_false_when_failures_exist(self) -> None:
        batch = CertificationBatchAggregate()
        batch.start()
        batch.complete(passed=520, failed=4, unexecutable=0)
        assert batch.all_passed is False

    def test_all_passed_false_when_not_completed(self) -> None:
        batch = CertificationBatchAggregate()
        batch.start()
        assert batch.all_passed is False


class CertificationItemAggregateTest:
    """CertificationItemAggregate 三态状态机。"""

    def _make_item(self, expected: str = "isolated") -> CertificationItemAggregate:
        return CertificationItemAggregate(
            item_id="SEC-ITEM-jwt-select-IAM:User",
            layer=IsolationLayer.JWT,
            operation=NineOperation.SELECT,
            aggregate_root="User",
            expected_behavior=expected,
        )

    def test_initial_state_is_pending(self) -> None:
        item = self._make_item()
        assert item.conclusion == Conclusion.PENDING
        assert not item.is_pass and not item.is_fail and not item.is_unexecutable

    def test_execute_transitions_pending_to_executing(self) -> None:
        item = self._make_item()
        item.execute()
        assert item.conclusion == Conclusion.EXECUTING
        assert item.executed_at is not None

    def test_execute_when_not_pending_raises(self) -> None:
        item = self._make_item()
        item.execute()
        with pytest.raises(SECError) as exc:
            item.execute()
        assert exc.value.code == SECErrorCode.CERT_ALREADY_RUNNING

    def test_judge_pass_when_behavior_matches_and_evidence_complete(self) -> None:
        item = self._make_item(expected="isolated")
        item.execute()
        item.capture_evidence(_full_evidence())
        item.judge(actual_behavior="isolated", duration_ms=120.0)
        assert item.conclusion == Conclusion.PASS
        assert item.is_pass

    def test_judge_fail_when_behavior_mismatches(self) -> None:
        item = self._make_item(expected="isolated")
        item.execute()
        item.capture_evidence(_full_evidence())
        item.judge(actual_behavior="leaked", duration_ms=120.0)
        assert item.conclusion == Conclusion.FAIL
        assert "Expected 'isolated', got 'leaked'" in item.failure_reason

    def test_judge_fail_when_evidence_missing(self) -> None:
        item = self._make_item(expected="isolated")
        item.execute()
        # 不 capture_evidence
        item.judge(actual_behavior="isolated", duration_ms=120.0)
        assert item.conclusion == Conclusion.FAIL
        assert "Evidence missing" in item.failure_reason

    def test_judge_fail_when_evidence_incomplete(self) -> None:
        item = self._make_item(expected="isolated")
        item.execute()
        item.capture_evidence(EvidenceSnapshot(request_log={}, response_log={}))
        item.judge(actual_behavior="isolated", duration_ms=120.0)
        assert item.conclusion == Conclusion.FAIL

    def test_evidence_verify_completeness_false_when_response_log_empty(self) -> None:
        # 覆盖 EvidenceSnapshot.verify_completeness line 24: request_log 非空但 response_log 空
        ev = EvidenceSnapshot(request_log={"m": "GET"}, response_log={})
        assert ev.verify_completeness() is False

    def test_evidence_verify_completeness_true_when_both_present(self) -> None:
        ev = EvidenceSnapshot(request_log={"m": "GET"}, response_log={"s": 200})
        assert ev.verify_completeness() is True

    def test_judge_fail_on_timeout(self) -> None:
        item = self._make_item(expected="isolated")
        item.execute()
        item.capture_evidence(_full_evidence())
        item.judge(actual_behavior="isolated", duration_ms=6000.0)
        assert item.conclusion == Conclusion.FAIL
        assert "Timeout" in item.failure_reason

    def test_judge_when_not_executing_raises(self) -> None:
        item = self._make_item()
        with pytest.raises(SECError) as exc:
            item.judge(actual_behavior="isolated", duration_ms=100.0)
        assert exc.value.code == SECErrorCode.CERT_ISSUE_FAILED

    def test_mark_unexecutable_transitions_executing_to_unexecutable(self) -> None:
        item = self._make_item()
        item.execute()
        item.mark_unexecutable("layer not deployed")
        assert item.conclusion == Conclusion.UNEXECUTABLE
        assert item.is_unexecutable
        assert item.failure_reason == "layer not deployed"

    def test_mark_unexecutable_when_not_executing_raises(self) -> None:
        item = self._make_item()
        with pytest.raises(SECError) as exc:
            item.mark_unexecutable("nope")
        assert exc.value.code == SECErrorCode.CERT_ISSUE_FAILED

    def test_capture_evidence_stores_snapshot(self) -> None:
        item = self._make_item()
        ev = _full_evidence()
        item.capture_evidence(ev)
        assert item.evidence is ev


class CertificationReportAggregateTest:
    """CertificationReportAggregate JSON/HTML 渲染。"""

    def _make_items(self) -> list[CertificationItemAggregate]:
        passing = CertificationItemAggregate(
            item_id="i1", expected_behavior="isolated", conclusion=Conclusion.PASS
        )
        failing = CertificationItemAggregate(
            item_id="i2",
            layer=IsolationLayer.RLS,
            expected_behavior="isolated",
            conclusion=Conclusion.FAIL,
            failure_reason="rls bypass",
        )
        unexecutable = CertificationItemAggregate(
            item_id="i3", expected_behavior="isolated", conclusion=Conclusion.UNEXECUTABLE
        )
        return [passing, failing, unexecutable]

    def test_calculate_statistics_counts_pass_fail_unexecutable(self) -> None:
        report = CertificationReportAggregate(report_id="RPT-1")
        report.calculate_statistics(self._make_items())
        assert report.total_items == 3
        assert report.passed_count == 1
        assert report.failed_count == 1
        assert report.unexecutable_count == 1
        assert report.failed_items == [
            {"item_id": "i2", "layer": "rls", "reason": "rls bypass"}
        ]

    def test_pass_rate_calculation(self) -> None:
        report = CertificationReportAggregate(report_id="RPT-1")
        report.calculate_statistics(self._make_items())
        assert report.pass_rate == pytest.approx(1 / 3)

    def test_pass_rate_zero_when_no_items(self) -> None:
        report = CertificationReportAggregate()
        assert report.pass_rate == 0.0

    def test_render_json_returns_valid_json_string(self) -> None:
        report = CertificationReportAggregate(
            report_id="RPT-1",
            matrix_version="1.0",
            executor="sec-bot",
        )
        report.calculate_statistics(self._make_items())
        rendered = report.render_json()
        payload = json.loads(rendered)
        assert payload["report_id"] == "RPT-1"
        assert payload["matrix_version"] == "1.0"
        assert payload["executor"] == "sec-bot"
        assert payload["total_items"] == 3
        assert payload["passed_count"] == 1
        assert payload["failed_count"] == 1
        assert payload["unexecutable_count"] == 1
        assert payload["pass_rate"] == round(1 / 3, 4)
        assert payload["failed_items"][0]["item_id"] == "i2"
        # 内部 report_json 同步更新
        assert report.report_json["report_id"] == "RPT-1"

    def test_render_html_contains_summary_and_failed_items(self) -> None:
        report = CertificationReportAggregate(
            report_id="RPT-1", matrix_version="1.0", executor="sec-bot"
        )
        report.calculate_statistics(self._make_items())
        html = report.render_html()
        assert "<!DOCTYPE html>" in html
        assert "Multi-Tenant Isolation Certification Report" in html
        assert "RPT-1" in html
        assert "Total Items</th><td>3" in html
        assert "Passed</th><td>1" in html
        assert "i2 (rls): rls bypass" in html
        assert report.report_html == html


class CertificationCertificateAggregateTest:
    """CertificationCertificateAggregate HMAC-SHA256 签名与状态机。"""

    _SIGNING_KEY = b"super-secret-signing-key"

    def _make_cert(self) -> CertificationCertificateAggregate:
        cert = CertificationCertificateAggregate(
            cert_number="SEC-CERT-20260101-ABCD1234",
            matrix_version="1.0",
            issuer="sec-issuer",
            signer="sec-signer",
        )
        cert.compute_evidence_hash(b'{"evidence": "full"}')
        return cert

    def test_compute_evidence_hash_sets_sha256_hex(self) -> None:
        cert = CertificationCertificateAggregate(cert_number="C1", matrix_version="1.0")
        cert.compute_evidence_hash(b"abc")
        assert len(cert.evidence_hash) == 64
        assert all(c in "0123456789abcdef" for c in cert.evidence_hash)

    def test_sign_transitions_draft_to_signed(self) -> None:
        cert = self._make_cert()
        cert.sign(self._SIGNING_KEY)
        assert cert.status == CertStatus.SIGNED
        assert len(cert.signature) == 64

    def test_sign_when_not_draft_raises(self) -> None:
        cert = self._make_cert()
        cert.sign(self._SIGNING_KEY)
        with pytest.raises(SECError) as exc:
            cert.sign(self._SIGNING_KEY)
        assert exc.value.code == SECErrorCode.CERT_SIGN_FAILED

    def test_sign_without_evidence_hash_raises(self) -> None:
        cert = CertificationCertificateAggregate(cert_number="C1", matrix_version="1.0")
        with pytest.raises(SECError) as exc:
            cert.sign(self._SIGNING_KEY)
        assert exc.value.code == SECErrorCode.EVIDENCE_MISSING

    def test_activate_transitions_signed_to_active(self) -> None:
        cert = self._make_cert()
        cert.sign(self._SIGNING_KEY)
        cert.activate()
        assert cert.status == CertStatus.ACTIVE
        assert cert.is_valid()

    def test_activate_when_draft_raises(self) -> None:
        cert = self._make_cert()
        with pytest.raises(SECError) as exc:
            cert.activate()
        assert exc.value.code == SECErrorCode.CERT_ISSUE_FAILED

    def test_verify_returns_true_with_correct_key(self) -> None:
        cert = self._make_cert()
        cert.sign(self._SIGNING_KEY)
        assert cert.verify(self._SIGNING_KEY) is True

    def test_verify_returns_false_with_wrong_key(self) -> None:
        cert = self._make_cert()
        cert.sign(self._SIGNING_KEY)
        assert cert.verify(b"wrong-key") is False

    def test_verify_detects_tampered_signature(self) -> None:
        cert = self._make_cert()
        cert.sign(self._SIGNING_KEY)
        cert.signature = "0" * 64  # 篡改
        assert cert.verify(self._SIGNING_KEY) is False

    def test_revoke_transitions_active_to_revoked(self) -> None:
        cert = self._make_cert()
        cert.sign(self._SIGNING_KEY)
        cert.activate()
        cert.revoke("incident #42")
        assert cert.status == CertStatus.REVOKED
        assert not cert.is_valid()

    def test_revoke_when_draft_raises(self) -> None:
        cert = self._make_cert()
        with pytest.raises(SECError) as exc:
            cert.revoke("nope")
        assert exc.value.code == SECErrorCode.CERT_ISSUE_FAILED

    def test_is_expired_true_when_valid_until_in_past(self) -> None:
        cert = self._make_cert()
        cert.valid_until = datetime.now(timezone.utc) - timedelta(days=1)
        assert cert.is_expired() is True

    def test_is_expired_false_when_valid_until_in_future(self) -> None:
        cert = self._make_cert()
        cert.valid_until = datetime.now(timezone.utc) + timedelta(days=30)
        assert cert.is_expired() is False

    def test_is_valid_false_when_not_active(self) -> None:
        cert = self._make_cert()
        cert.sign(self._SIGNING_KEY)
        # SIGNED but not ACTIVE
        assert cert.is_valid() is False

    def test_invalid_transition_expired_to_anything_raises(self) -> None:
        cert = self._make_cert()
        cert.sign(self._SIGNING_KEY)
        cert.activate()
        # 模拟过期后尝试撤销 - REVOKED 在 ACTIVE 的合法转移中，所以这里测 EXPIRED 终态
        cert.status = CertStatus.EXPIRED
        with pytest.raises(SECError):
            cert.revoke("late")


class CertificationConfigAggregateTest:
    """CertificationConfigAggregate 配置更新与跳过。"""

    def test_default_matrix_layers_has_15_entries(self) -> None:
        config = CertificationConfigAggregate()
        assert len(config.matrix_layers) == 15

    def test_default_alert_channels(self) -> None:
        config = CertificationConfigAggregate()
        assert config.alert_channels == ["email", "webhook"]

    def test_update_changes_fields_and_timestamp(self) -> None:
        config = CertificationConfigAggregate()
        before = config.updated_at
        config.update(strict_mode=False, report_retention_days=180)
        assert config.strict_mode is False
        assert config.report_retention_days == 180
        assert config.updated_at >= before

    def test_skip_item_records_reason(self) -> None:
        config = CertificationConfigAggregate()
        config.skip_item("SEC-ITEM-e2e-step-01", "e2e not applicable in staging")
        assert config.is_skipped("SEC-ITEM-e2e-step-01") is True
        assert config.is_skipped("SEC-ITEM-jwt-select-IAM:User") is False

    def test_skip_item_with_empty_reason_raises(self) -> None:
        config = CertificationConfigAggregate()
        with pytest.raises(SECError) as exc:
            config.skip_item("i1", "")
        assert exc.value.code == SECErrorCode.SKIP_REASON_REQUIRED


class CertificationAuditAggregateTest:
    """CertificationAuditAggregate append-only 与篡改检测。"""

    def test_append_populates_fields(self) -> None:
        audit = CertificationAuditAggregate()
        batch_id = uuid4()
        tenant_id = uuid4()
        audit.append(
            action_type=AuditActionType.ITEM_PASS,
            operator="sec-bot",
            batch_id=batch_id,
            tenant_id=tenant_id,
            item_id="SEC-ITEM-jwt-select-IAM:User",
            before_value={"status": "pending"},
            after_value={"status": "pass"},
            evidence={"log": "ok"},
        )
        assert audit.action_type == AuditActionType.ITEM_PASS
        assert audit.operator == "sec-bot"
        assert audit.batch_id == batch_id
        assert audit.tenant_id == tenant_id
        assert audit.item_id == "SEC-ITEM-jwt-select-IAM:User"
        assert audit.after_value == {"status": "pass"}
        assert audit.evidence == {"log": "ok"}
        assert audit.immutable is True

    def test_append_with_none_evidence_defaults_to_empty_dict(self) -> None:
        audit = CertificationAuditAggregate()
        audit.append(
            action_type=AuditActionType.CERT_EXECUTE,
            operator="op",
            batch_id=uuid4(),
            tenant_id=uuid4(),
            evidence=None,
        )
        assert audit.evidence == {}

    def test_attempt_tamper_raises(self) -> None:
        audit = CertificationAuditAggregate()
        with pytest.raises(SECError) as exc:
            audit.attempt_tamper()
        assert exc.value.code == SECErrorCode.AUDIT_TAMPER_ATTEMPT

    def test_update_raises_tamper(self) -> None:
        audit = CertificationAuditAggregate()
        with pytest.raises(SECError) as exc:
            audit.update(operator="malicious")
        assert exc.value.code == SECErrorCode.AUDIT_TAMPER_ATTEMPT

    def test_delete_raises_tamper(self) -> None:
        audit = CertificationAuditAggregate()
        with pytest.raises(SECError) as exc:
            audit.delete()
        assert exc.value.code == SECErrorCode.AUDIT_TAMPER_ATTEMPT

    def test_retention_expired_always_false(self) -> None:
        audit = CertificationAuditAggregate()
        assert audit.retention_expired is False