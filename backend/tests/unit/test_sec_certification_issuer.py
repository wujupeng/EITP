"""EITP-SEC-001 证书签发/校验/撤销服务单元测试。

覆盖:
- CertificationIssuer: 全通过签发、失败拒绝、HMAC-SHA256 签名
- CertificationVerifier: 签名/状态/有效期/撤销校验
- CertificationRevocationService: 撤销与终态判定
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from app.application.sec.certification_issuer import CertificationIssuer
from app.application.sec.certification_revocation_service import (
    CertificationRevocationService,
)
from app.application.sec.certification_verifier import (
    CertificationVerifier,
    VerificationResult,
)
from app.domain.sec.certification.aggregates.certification_certificate_aggregate import (
    CertificationCertificateAggregate,
)
from app.domain.sec.certification.value_objects.cert_status import CertStatus
from app.interfaces.middleware.error_handler import SECError, SECErrorCode

_SIGNING_KEY = b"issuer-signing-key-2026"
_REQUIRED_TOTAL_ITEMS = 524


def _evidence_data(n: int = 524) -> list[dict[str, object]]:
    return [{"item_id": f"SEC-ITEM-{i}", "result": "pass"} for i in range(n)]


def _issue_valid_cert() -> CertificationCertificateAggregate:
    issuer = CertificationIssuer(_SIGNING_KEY)
    return issuer.issue(
        matrix_version="1.0",
        total_items=_REQUIRED_TOTAL_ITEMS,
        passed_count=_REQUIRED_TOTAL_ITEMS,
        failed_count=0,
        unexecutable_count=0,
        evidence_data=_evidence_data(),
        issuer="sec-issuer",
        signer="sec-signer",
        tenant_id=uuid4(),
    )


class CertificationIssuerTest:
    """CertificationIssuer 签发行为。"""

    def test_issue_returns_signed_active_certificate(self) -> None:
        cert = _issue_valid_cert()
        assert cert.status == CertStatus.ACTIVE
        assert cert.matrix_version == "1.0"
        assert cert.cert_number.startswith("SEC-CERT-")
        assert len(cert.evidence_hash) == 64
        assert len(cert.signature) == 64
        assert cert.valid_until > cert.issued_at

    def test_issue_rejects_when_failures_exist(self) -> None:
        issuer = CertificationIssuer(_SIGNING_KEY)
        with pytest.raises(SECError) as exc:
            issuer.issue(
                matrix_version="1.0",
                total_items=_REQUIRED_TOTAL_ITEMS,
                passed_count=520,
                failed_count=4,
                unexecutable_count=0,
                evidence_data=_evidence_data(),
                issuer="sec-issuer",
                signer="sec-signer",
                tenant_id=uuid4(),
            )
        assert exc.value.code == SECErrorCode.CERT_PREREQUISITE_NOT_MET
        assert "4 failed" in exc.value.message

    def test_issue_rejects_when_unexecutable_exist(self) -> None:
        issuer = CertificationIssuer(_SIGNING_KEY)
        with pytest.raises(SECError) as exc:
            issuer.issue(
                matrix_version="1.0",
                total_items=_REQUIRED_TOTAL_ITEMS,
                passed_count=510,
                failed_count=0,
                unexecutable_count=14,
                evidence_data=_evidence_data(),
                issuer="sec-issuer",
                signer="sec-signer",
                tenant_id=uuid4(),
            )
        assert exc.value.code == SECErrorCode.CERT_PREREQUISITE_NOT_MET
        assert "14 unexecutable" in exc.value.message

    def test_issue_rejects_when_total_items_below_threshold(self) -> None:
        issuer = CertificationIssuer(_SIGNING_KEY)
        with pytest.raises(SECError) as exc:
            issuer.issue(
                matrix_version="1.0",
                total_items=400,
                passed_count=400,
                failed_count=0,
                unexecutable_count=0,
                evidence_data=_evidence_data(400),
                issuer="sec-issuer",
                signer="sec-signer",
                tenant_id=uuid4(),
            )
        assert exc.value.code == SECErrorCode.CERT_PREREQUISITE_NOT_MET
        assert "requires 524" in exc.value.message

    def test_issue_signature_verifies_with_same_key(self) -> None:
        cert = _issue_valid_cert()
        assert cert.verify(_SIGNING_KEY) is True

    def test_issue_signature_does_not_verify_with_wrong_key(self) -> None:
        cert = _issue_valid_cert()
        assert cert.verify(b"wrong-key") is False

    def test_issue_evidence_hash_is_deterministic_for_same_evidence(self) -> None:
        issuer = CertificationIssuer(_SIGNING_KEY)
        common_args = dict(
            matrix_version="1.0",
            total_items=_REQUIRED_TOTAL_ITEMS,
            passed_count=_REQUIRED_TOTAL_ITEMS,
            failed_count=0,
            unexecutable_count=0,
            evidence_data=_evidence_data(),
            issuer="sec-issuer",
            signer="sec-signer",
            tenant_id=uuid4(),
        )
        cert_a = issuer.issue(**common_args)
        cert_b = issuer.issue(**common_args)
        assert cert_a.evidence_hash == cert_b.evidence_hash

    def test_issue_cert_scope_default_when_not_provided(self) -> None:
        cert = _issue_valid_cert()
        assert cert.cert_scope["layers"] == 15
        assert cert.cert_scope["modules"] == 7
        assert cert.cert_scope["total_items"] == _REQUIRED_TOTAL_ITEMS

    def test_issue_cert_scope_custom_when_provided(self) -> None:
        issuer = CertificationIssuer(_SIGNING_KEY)
        cert = issuer.issue(
            matrix_version="1.0",
            total_items=_REQUIRED_TOTAL_ITEMS,
            passed_count=_REQUIRED_TOTAL_ITEMS,
            failed_count=0,
            unexecutable_count=0,
            evidence_data=_evidence_data(),
            issuer="sec-issuer",
            signer="sec-signer",
            tenant_id=uuid4(),
            cert_scope={"custom": True},
        )
        assert cert.cert_scope == {"custom": True}


class CertificationVerifierTest:
    """CertificationVerifier 四维校验。"""

    def test_verify_valid_active_cert_overall_valid(self) -> None:
        cert = _issue_valid_cert()
        verifier = CertificationVerifier(_SIGNING_KEY)
        result = verifier.verify(cert)
        assert isinstance(result, VerificationResult)
        assert result.signature_valid is True
        assert result.status_valid is True
        assert result.not_expired is True
        assert result.not_revoked is True
        assert result.overall_valid is True

    def test_verify_detects_tampered_signature(self) -> None:
        cert = _issue_valid_cert()
        cert.signature = "0" * 64
        verifier = CertificationVerifier(_SIGNING_KEY)
        result = verifier.verify(cert)
        assert result.signature_valid is False
        assert result.overall_valid is False

    def test_verify_detects_revoked_status(self) -> None:
        cert = _issue_valid_cert()
        cert.revoke("incident")
        verifier = CertificationVerifier(_SIGNING_KEY)
        result = verifier.verify(cert)
        assert result.not_revoked is False
        assert result.overall_valid is False

    def test_verify_detects_expired_cert(self) -> None:
        cert = _issue_valid_cert()
        cert.valid_until = datetime.now(timezone.utc) - timedelta(days=1)
        verifier = CertificationVerifier(_SIGNING_KEY)
        result = verifier.verify(cert)
        assert result.not_expired is False
        assert result.overall_valid is False

    def test_verify_status_valid_for_signed_state(self) -> None:
        # 构造仅 SIGNED 状态证书
        cert = CertificationCertificateAggregate(
            cert_number="SEC-CERT-X", matrix_version="1.0"
        )
        cert.compute_evidence_hash(b"evidence")
        cert.sign(_SIGNING_KEY)
        verifier = CertificationVerifier(_SIGNING_KEY)
        result = verifier.verify(cert)
        assert result.signature_valid is True
        assert result.status_valid is True  # SIGNED 视为状态有效

    def test_verify_status_invalid_for_draft_state(self) -> None:
        cert = CertificationCertificateAggregate(
            cert_number="SEC-CERT-X", matrix_version="1.0"
        )
        cert.compute_evidence_hash(b"evidence")
        verifier = CertificationVerifier(_SIGNING_KEY)
        result = verifier.verify(cert)
        assert result.status_valid is False
        assert result.overall_valid is False

    def test_verify_with_wrong_key_fails_signature(self) -> None:
        cert = _issue_valid_cert()
        verifier = CertificationVerifier(b"different-key")
        result = verifier.verify(cert)
        assert result.signature_valid is False
        assert result.overall_valid is False


class CertificationRevocationServiceTest:
    """CertificationRevocationService 撤销行为。"""

    def test_revoke_transitions_active_to_revoked(self) -> None:
        cert = _issue_valid_cert()
        service = CertificationRevocationService()
        revoked = service.revoke(cert, "security incident #42")
        assert revoked.status == CertStatus.REVOKED
        assert revoked is cert

    def test_revoke_already_revoked_raises(self) -> None:
        cert = _issue_valid_cert()
        service = CertificationRevocationService()
        service.revoke(cert, "first reason")
        with pytest.raises(SECError) as exc:
            service.revoke(cert, "second reason")
        assert exc.value.code == SECErrorCode.CERT_REVOKED_USED

    def test_is_revocation_final_true_for_revoked(self) -> None:
        cert = _issue_valid_cert()
        service = CertificationRevocationService()
        service.revoke(cert, "reason")
        assert service.is_revocation_final(cert) is True

    def test_is_revocation_final_false_for_active(self) -> None:
        cert = _issue_valid_cert()
        service = CertificationRevocationService()
        assert service.is_revocation_final(cert) is False