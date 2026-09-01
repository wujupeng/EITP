"""CertificationIssuer - 证书颁发服务。"""

from __future__ import annotations

import hashlib
import hmac
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID, uuid4

from app.domain.sec.certification.aggregates.certification_certificate_aggregate import (
    CertificationCertificateAggregate,
)
from app.domain.sec.certification.value_objects.cert_status import CertStatus
from app.interfaces.middleware.error_handler import SECError, SECErrorCode

_CERT_VALIDITY_DAYS = 90
_REQUIRED_TOTAL_ITEMS = 524


class CertificationIssuer:
    """校验全通过前提 → 生成证据哈希 → HMAC-SHA256 签名 → 持久化。"""

    def __init__(self, signing_key: bytes) -> None:
        self._signing_key = signing_key

    def issue(
        self,
        matrix_version: str,
        total_items: int,
        passed_count: int,
        failed_count: int,
        unexecutable_count: int,
        evidence_data: list[dict[str, Any]],
        issuer: str,
        signer: str,
        tenant_id: UUID,
        cert_scope: dict[str, Any] | None = None,
    ) -> CertificationCertificateAggregate:
        if failed_count > 0 or unexecutable_count > 0:
            raise SECError(
                SECErrorCode.CERT_PREREQUISITE_NOT_MET,
                f"Cannot issue certificate: {failed_count} failed, {unexecutable_count} unexecutable (all must pass)",
            )

        if total_items < _REQUIRED_TOTAL_ITEMS:
            raise SECError(
                SECErrorCode.CERT_PREREQUISITE_NOT_MET,
                f"Cannot issue certificate: only {total_items} items executed (requires {_REQUIRED_TOTAL_ITEMS})",
            )

        evidence_json = str(sorted(evidence_data, key=lambda x: str(x)))
        evidence_hash = hashlib.sha256(evidence_json.encode()).hexdigest()

        cert = CertificationCertificateAggregate(
            certificate_id=uuid4(),
            cert_number=f"SEC-CERT-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{uuid4().hex[:8].upper()}",
            matrix_version=matrix_version,
            cert_scope=cert_scope or {"layers": 15, "modules": 7, "total_items": total_items},
            issued_at=datetime.now(timezone.utc),
            valid_until=datetime.now(timezone.utc) + timedelta(days=_CERT_VALIDITY_DAYS),
            issuer=issuer,
            signer=signer,
            evidence_hash=evidence_hash,
            status=CertStatus.DRAFT,
            tenant_id=tenant_id,
        )

        cert.sign(self._signing_key)
        cert.activate()
        return cert