"""V16_SEC_RECERT 验证器测试。"""

from __future__ import annotations

import asyncio
from tests.verifiers import make_config
from app.application.prod.verifiers.v16_sec_recertification_verifier import SecRecertificationVerifier
from app.domain.prod.engine.enums import VerificationConclusion, VerificationItem


class TestSecRecertificationVerifier:
    def setup_method(self):
        self.verifier = SecRecertificationVerifier()

    def test_item_is_correct(self):
        assert self.verifier.item == VerificationItem.SEC_RECERT

    def test_pass_with_default_config(self):
        config = make_config(parameters={})
        result = asyncio.run(self.verifier.execute(config))
        assert result.conclusion == VerificationConclusion.PASS

    def test_report_contains_verification_item(self):
        config = make_config(parameters={})
        result = asyncio.run(self.verifier.execute(config))
        assert result.report["verification_item"] == "V16_SEC_RECERT"
