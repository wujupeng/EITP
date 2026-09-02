"""V01 性能基线验证器测试。"""

from __future__ import annotations

from tests.verifiers import make_config
from app.application.prod.verifiers.v01_performance_baseline_verifier import PerformanceBaselineVerifier
from app.domain.prod.engine.enums import VerificationConclusion, VerificationItem
from app.domain.prod.error_codes import PRODErrorCode


class TestV01PerformanceBaselineVerifier:
    def setup_method(self):
        self.verifier = PerformanceBaselineVerifier()

    def test_item_is_baseline(self):
        assert self.verifier.item == VerificationItem.BASELINE

    def test_pass_when_all_endpoints_meet_thresholds(self):
        config = make_config(parameters={"endpoints": [{"path": "/api/v1/inv/products", "method": "GET"}], "samples_per_endpoint": 10000})
        result = self.verifier.execute(config)
        import asyncio
        result = asyncio.run(self.verifier.execute(config))
        assert result.conclusion == VerificationConclusion.PASS

    def test_fail_when_insufficient_samples(self):
        config = make_config(parameters={"endpoints": [{"path": "/api/test", "method": "GET"}], "samples_per_endpoint": 100})
        import asyncio
        result = asyncio.run(self.verifier.execute(config))
        assert result.conclusion == VerificationConclusion.FAIL
        assert result.failure_code == PRODErrorCode.BASELINE_INSUFFICIENT_SAMPLES.value

    def test_report_contains_verification_item(self):
        config = make_config(parameters={"endpoints": [], "samples_per_endpoint": 10000})
        import asyncio
        result = asyncio.run(self.verifier.execute(config))
        assert result.report["verification_item"] == "V01_BASELINE"