"""Certification 颁发全流程 E2E 测试。"""

import pytest
from uuid import uuid4

from app.application.sec.certification_issuer import CertificationIssuer
from app.application.sec.certification_verifier import CertificationVerifier
from app.application.sec.certification_revocation_service import CertificationRevocationService
from app.domain.sec.certification.value_objects.cert_status import CertStatus
from app.interfaces.middleware.error_handler import SECError, SECErrorCode


_SIGNING_KEY = b"test-signing-key-for-e2e"


class TestCertificationIssuanceE2E:
    """524 认证项全 PASS → 颁发证书 → 签名校验 → 撤销 → 重新认证。"""

    def test_issue_with_all_pass(self) -> None:
        issuer = CertificationIssuer(_SIGNING_KEY)
        cert = issuer.issue(
            matrix_version="e2e-v1",
            total_items=524,
            passed_count=524,
            failed_count=0,
            unexecutable_count=0,
            evidence_data=[{"item_id": f"item-{i}"} for i in range(524)],
            issuer="admin",
            signer="security",
            tenant_id=uuid4(),
        )
        assert cert.status == CertStatus.ACTIVE
        assert cert.cert_number.startswith("SEC-CERT-")

    def test_issue_rejects_with_failures(self) -> None:
        issuer = CertificationIssuer(_SIGNING_KEY)
        with pytest.raises(SECError):
            issuer.issue(
                matrix_version="e2e-v1",
                total_items=524,
                passed_count=523,
                failed_count=1,
                unexecutable_count=0,
                evidence_data=[],
                issuer="admin",
                signer="security",
                tenant_id=uuid4(),
            )

    def test_verify_valid_certificate(self) -> None:
        issuer = CertificationIssuer(_SIGNING_KEY)
        cert = issuer.issue(
            matrix_version="e2e-v1",
            total_items=524,
            passed_count=524,
            failed_count=0,
            unexecutable_count=0,
            evidence_data=[],
            issuer="admin",
            signer="security",
            tenant_id=uuid4(),
        )
        verifier = CertificationVerifier(_SIGNING_KEY)
        result = verifier.verify(cert)
        assert result.overall_valid is True

    def test_revoke_certificate(self) -> None:
        issuer = CertificationIssuer(_SIGNING_KEY)
        cert = issuer.issue(
            matrix_version="e2e-v1",
            total_items=524,
            passed_count=524,
            failed_count=0,
            unexecutable_count=0,
            evidence_data=[],
            issuer="admin",
            signer="security",
            tenant_id=uuid4(),
        )
        revocation = CertificationRevocationService()
        revoked = revocation.revoke(cert, "security incident")
        assert revoked.status == CertStatus.REVOKED

    def test_revoke_already_revoked_raises(self) -> None:
        issuer = CertificationIssuer(_SIGNING_KEY)
        cert = issuer.issue(
            matrix_version="e2e-v1",
            total_items=524,
            passed_count=524,
            failed_count=0,
            unexecutable_count=0,
            evidence_data=[],
            issuer="admin",
            signer="security",
            tenant_id=uuid4(),
        )
        revocation = CertificationRevocationService()
        revocation.revoke(cert, "first revocation")
        with pytest.raises(SECError):
            revocation.revoke(cert, "second revocation")