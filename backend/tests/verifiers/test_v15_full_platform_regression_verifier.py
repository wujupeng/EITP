"""V15_REGRESSION 验证器测试。"""

from __future__ import annotations

import asyncio
from tests.verifiers import make_config
from app.application.prod.verifiers.v15_full_platform_regression_verifier import FullPlatformRegressionVerifier
from app.domain.prod.engine.enums import VerificationConclusion, VerificationItem


class TestFullPlatformRegressionVerifier:
    def setup_method(self):
        self.verifier = FullPlatformRegressionVerifier()

    def test_item_is_correct(self):
        assert self.verifier.item == VerificationItem.REGRESSION

    def test_pass_with_default_config(self):
        config = make_config(parameters={})
        result = asyncio.run(self.verifier.execute(config))
        assert result.conclusion == VerificationConclusion.PASS

    def test_report_contains_verification_item(self):
        config = make_config(parameters={})
        result = asyncio.run(self.verifier.execute(config))
        assert result.report["verification_item"] == "V15_REGRESSION"
