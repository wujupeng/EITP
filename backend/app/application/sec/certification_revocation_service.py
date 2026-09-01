"""CertificationRevocationService - 证书撤销服务。"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.domain.sec.certification.aggregates.certification_certificate_aggregate import (
    CertificationCertificateAggregate,
)
from app.domain.sec.certification.value_objects.cert_status import CertStatus
from app.interfaces.middleware.error_handler import SECError, SECErrorCode


class CertificationRevocationService:
    """状态流转到 REVOKED + 撤销记录不可篡改 + 触发重新认证。"""

    def revoke(self, cert: CertificationCertificateAggregate, reason: str) -> CertificationCertificateAggregate:
        if cert.status == CertStatus.REVOKED:
            raise SECError(SECErrorCode.CERT_REVOKED_USED, f"Certificate {cert.cert_number} already revoked")
        cert.revoke(reason)
        return cert

    def is_revocation_final(self, cert: CertificationCertificateAggregate) -> bool:
        return cert.status == CertStatus.REVOKED