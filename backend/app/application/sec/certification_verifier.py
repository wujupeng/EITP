"""CertificationVerifier - 证书校验服务。"""

from __future__ import annotations

from dataclasses import dataclass

from app.domain.sec.certification.aggregates.certification_certificate_aggregate import (
    CertificationCertificateAggregate,
)
from app.domain.sec.certification.value_objects.cert_status import CertStatus


@dataclass
class VerificationResult:
    signature_valid: bool = False
    status_valid: bool = False
    not_expired: bool = False
    not_revoked: bool = False
    overall_valid: bool = False


class CertificationVerifier:
    """签名校验 + 状态校验 + 有效期校验 + 篡改检测。"""

    def __init__(self, signing_key: bytes) -> None:
        self._signing_key = signing_key

    def verify(self, cert: CertificationCertificateAggregate) -> VerificationResult:
        result = VerificationResult()

        result.signature_valid = cert.verify(self._signing_key)
        result.status_valid = cert.status in (CertStatus.ACTIVE, CertStatus.SIGNED)
        result.not_expired = not cert.is_expired()
        result.not_revoked = cert.status != CertStatus.REVOKED
        result.overall_valid = all([
            result.signature_valid,
            result.status_valid,
            result.not_expired,
            result.not_revoked,
        ])

        return result