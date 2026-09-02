"""V11_DR 验证器测试。"""

from __future__ import annotations

import asyncio
from tests.verifiers import make_config
from app.application.prod.verifiers.v11_disaster_recovery_drill_verifier import DisasterRecoveryDrillVerifier
from app.domain.prod.engine.enums import VerificationConclusion, VerificationItem


class TestDisasterRecoveryDrillVerifier:
    def setup_method(self):
        self.verifier = DisasterRecoveryDrillVerifier()

    def test_item_is_correct(self):
        assert self.verifier.item == VerificationItem.DR

    def test_pass_with_default_config(self):
        config = make_config(parameters={"sre_authorized": True, "sec_off_authorized": True})
        result = asyncio.run(self.verifier.execute(config))
        assert result.conclusion == VerificationConclusion.PASS

    def test_report_contains_verification_item(self):
        config = make_config(parameters={"sre_authorized": True, "sec_off_authorized": True})
        result = asyncio.run(self.verifier.execute(config))
        assert result.report["verification_item"] == "V11_DR"
