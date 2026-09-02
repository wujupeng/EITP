"""V13_RATELIMIT 验证器测试。"""

from __future__ import annotations

import asyncio
from tests.verifiers import make_config
from app.application.prod.verifiers.v13_rate_limit_verification_verifier import RateLimitVerificationVerifier
from app.domain.prod.engine.enums import VerificationConclusion, VerificationItem


class TestRateLimitVerificationVerifier:
    def setup_method(self):
        self.verifier = RateLimitVerificationVerifier()

    def test_item_is_correct(self):
        assert self.verifier.item == VerificationItem.RATELIMIT

    def test_pass_with_default_config(self):
        config = make_config(parameters={})
        result = asyncio.run(self.verifier.execute(config))
        assert result.conclusion == VerificationConclusion.PASS

    def test_report_contains_verification_item(self):
        config = make_config(parameters={})
        result = asyncio.run(self.verifier.execute(config))
        assert result.report["verification_item"] == "V13_RATELIMIT"
