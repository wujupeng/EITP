"""证书有效期校验器。"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from app.application.rel.gate_checkers.base_checker import GateChecker, GateResult
from app.domain.rel.enums import GateType
from app.domain.rel.error_codes import RELErrorCode


class CertValidityChecker(GateChecker):
    """校验 SEC 证书与 PROD 证明书有效期与签名。"""

    def __init__(
        self,
        sec_cert_repository: object | None = None,
        prod_dossier_repository: object | None = None,
    ) -> None:
        self._sec_cert_repo = sec_cert_repository
        self._prod_dossier_repo = prod_dossier_repository

    @property
    def gate_type(self) -> GateType:
        return GateType.CERT_VALIDITY

    async def check(self, release_id: UUID, executed_by: str) -> GateResult:
        now = datetime.now(timezone.utc)
        issues: list[dict] = []

        if self._sec_cert_repo is not None:
            try:
                certs = await self._sec_cert_repo.list_active_certs()
                for cert in certs:
                    valid_until = cert.get("valid_until")
                    if valid_until and valid_until < now:
                        issues.append({
                            "type": "sec_cert_expired",
                            "cert_id": str(cert.get("cert_id")),
                            "valid_until": valid_until.isoformat(),
                        })
                    if not cert.get("is_signed"):
                        issues.append({
                            "type": "sec_cert_unsigned",
                            "cert_id": str(cert.get("cert_id")),
                        })
            except Exception as e:
                issues.append({"type": "sec_cert_query_error", "error": str(e)})

        if self._prod_dossier_repo is not None:
            try:
                dossiers = await self._prod_dossier_repo.list_active_dossiers()
                for dossier in dossiers:
                    valid_until = dossier.get("valid_until")
                    if valid_until and valid_until < now:
                        issues.append({
                            "type": "prod_dossier_expired",
                            "dossier_id": str(dossier.get("dossier_id")),
                            "valid_until": valid_until.isoformat(),
                        })
                    if not dossier.get("signer"):
                        issues.append({
                            "type": "prod_dossier_unsigned",
                            "dossier_id": str(dossier.get("dossier_id")),
                        })
            except Exception as e:
                issues.append({"type": "prod_dossier_query_error", "error": str(e)})

        if issues:
            return GateResult(
                gate_type=self.gate_type,
                passed=False,
                detail={"issues": issues},
                error_code=RELErrorCode.GATE_CERT_INVALID.value,
                error_message=f"{len(issues)} cert/dossier issue(s)",
            )
        return GateResult(
            gate_type=self.gate_type,
            passed=True,
            detail={"checked_certs": True, "checked_dossiers": True},
        )