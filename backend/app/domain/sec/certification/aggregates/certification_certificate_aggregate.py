"""CertificationCertificateAggregate 聚合根 - 认证证书，HMAC-SHA256 签名 + 状态机。"""

from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from app.domain.sec.certification.value_objects.cert_status import CertStatus
from app.interfaces.middleware.error_handler import SECError, SECErrorCode


_VALID_TRANSITIONS: dict[CertStatus, set[CertStatus]] = {
    CertStatus.DRAFT: {CertStatus.SIGNED},
    CertStatus.SIGNED: {CertStatus.ACTIVE},
    CertStatus.ACTIVE: {CertStatus.EXPIRED, CertStatus.REVOKED},
    CertStatus.EXPIRED: set(),
    CertStatus.REVOKED: set(),
}


@dataclass
class CertificationCertificateAggregate:
    certificate_id: UUID = field(default_factory=uuid4)
    cert_number: str = ""
    matrix_version: str = ""
    cert_scope: dict = field(default_factory=dict)
    issued_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    valid_until: datetime = field(default_factory=lambda: datetime.now(timezone.utc) + timedelta(days=90))
    issuer: str = ""
    signer: str = ""
    evidence_hash: str = ""
    signature: str = ""
    status: CertStatus = CertStatus.DRAFT
    tenant_id: UUID = field(default_factory=lambda: UUID("00000000-0000-0000-0000-000000000000"))

    def _transition(self, target: CertStatus) -> None:
        if target not in _VALID_TRANSITIONS.get(self.status, set()):
            raise SECError(SECErrorCode.CERT_ISSUE_FAILED, f"Invalid transition {self.status} → {target}")
        self.status = target

    def compute_evidence_hash(self, evidence_data: bytes) -> None:
        self.evidence_hash = hashlib.sha256(evidence_data).hexdigest()

    def sign(self, signing_key: bytes) -> None:
        if self.status != CertStatus.DRAFT:
            raise SECError(SECErrorCode.CERT_SIGN_FAILED, "Certificate not in DRAFT state")
        if not self.evidence_hash:
            raise SECError(SECErrorCode.EVIDENCE_MISSING, "Evidence hash not computed")
        msg = f"{self.cert_number}:{self.matrix_version}:{self.evidence_hash}".encode()
        self.signature = hmac.new(signing_key, msg, hashlib.sha256).hexdigest()
        self._transition(CertStatus.SIGNED)

    def activate(self) -> None:
        self._transition(CertStatus.ACTIVE)

    def verify(self, signing_key: bytes) -> bool:
        msg = f"{self.cert_number}:{self.matrix_version}:{self.evidence_hash}".encode()
        expected = hmac.new(signing_key, msg, hashlib.sha256).hexdigest()
        return hmac.compare_digest(self.signature, expected)

    def revoke(self, reason: str) -> None:
        self._transition(CertStatus.REVOKED)

    def is_expired(self) -> bool:
        return datetime.now(timezone.utc) > self.valid_until or self.status == CertStatus.EXPIRED

    def is_valid(self) -> bool:
        return self.status == CertStatus.ACTIVE and not self.is_expired()