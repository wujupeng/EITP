"""PROD E2E 测试 - V17 证明书汇编 +- 签发。"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import pytest
from app.domain.prod.dossier.aggregates.production_readiness_dossier_aggregate import (
    ProductionReadinessDossierAggregate,
)
from app.domain.prod.engine.enums import DossierStatus, DossierVerdict
from datetime import datetime, timedelta, timezone
from uuid import uuid4


class TestProdDossierAssembleSignE2E:
    """V17 证明书汇编 + 9 问 + 签发 + FINAL PASS。"""

    def test_dossier_full_lifecycle(self):
        dossier = ProductionReadinessDossierAggregate.create(tenant_scope="platform")
        assert dossier.status == DossierStatus.DRAFT

        dossier = dossier.assemble(
            run_ids=[uuid4() for _ in range(16)],
            nine_questions_answers={"Q1": {"conclusion": "能"}},
            evidence_aggregate_hash="abc123",
        )
        assert len(dossier.verification_run_ids) == 16

        dossier = dossier.submit_for_signing()
        assert dossier.status == DossierStatus.PENDING_SIGN

        valid_until = datetime.now(timezone.utc) + timedelta(days=365)
        dossier = dossier.sign(signer="sec_officer", valid_until=valid_until)
        assert dossier.status == DossierStatus.SIGNED
        assert dossier.verdict == DossierVerdict.READY

    def test_dossier_invalid_after_sign(self):
        dossier = ProductionReadinessDossierAggregate.create(tenant_scope="platform")
        dossier = dossier.submit_for_signing()
        valid_until = datetime.now(timezone.utc) + timedelta(days=365)
        dossier = dossier.sign(signer="sec_officer", valid_until=valid_until)
        dossier = dossier.invalidate(reason="evidence tampered")
        assert dossier.status == DossierStatus.INVALID

    def test_dossier_cannot_sign_from_draft(self):
        from app.domain.prod.exceptions import PRODError
        dossier = ProductionReadinessDossierAggregate.create(tenant_scope="platform")
        with pytest.raises(PRODError):
            dossier.sign(signer="x", valid_until=datetime.now(timezone.utc))