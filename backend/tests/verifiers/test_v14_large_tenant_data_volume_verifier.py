"""V14_LARGE_TENANT 验证器测试。"""

from __future__ import annotations

import asyncio
from tests.verifiers import make_config
from app.application.prod.verifiers.v14_large_tenant_data_volume_verifier import LargeTenantDataVolumeVerifier
from app.domain.prod.engine.enums import VerificationConclusion, VerificationItem


class TestLargeTenantDataVolumeVerifier:
    def setup_method(self):
        self.verifier = LargeTenantDataVolumeVerifier()

    def test_item_is_correct(self):
        assert self.verifier.item == VerificationItem.LARGE_TENANT

    def test_pass_with_default_config(self):
        config = make_config(parameters={})
        result = asyncio.run(self.verifier.execute(config))
        assert result.conclusion == VerificationConclusion.PASS

    def test_report_contains_verification_item(self):
        config = make_config(parameters={})
        result = asyncio.run(self.verifier.execute(config))
        assert result.report["verification_item"] == "V14_LARGE_TENANT"
