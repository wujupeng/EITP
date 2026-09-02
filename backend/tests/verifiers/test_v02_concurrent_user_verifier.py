"""V02_CONCURRENT 验证器测试。"""

from __future__ import annotations

import asyncio
from tests.verifiers import make_config
from app.application.prod.verifiers.v02_concurrent_user_verifier import ConcurrentUserVerifier
from app.domain.prod.engine.enums import VerificationConclusion, VerificationItem


class TestConcurrentUserVerifier:
    def setup_method(self):
        self.verifier = ConcurrentUserVerifier()

    def test_item_is_correct(self):
        assert self.verifier.item == VerificationItem.CONCURRENT

    def test_pass_with_default_config(self):
        config = make_config(parameters={})
        result = asyncio.run(self.verifier.execute(config))
        assert result.conclusion == VerificationConclusion.PASS

    def test_report_contains_verification_item(self):
        config = make_config(parameters={})
        result = asyncio.run(self.verifier.execute(config))
        assert result.report["verification_item"] == "V02_CONCURRENT"
