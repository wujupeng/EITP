"""V05_OUTBOX 验证器测试。"""

from __future__ import annotations

import asyncio
from tests.verifiers import make_config
from app.application.prod.verifiers.v05_outbox_backlog_recovery_verifier import OutboxBacklogRecoveryVerifier
from app.domain.prod.engine.enums import VerificationConclusion, VerificationItem


class TestOutboxBacklogRecoveryVerifier:
    def setup_method(self):
        self.verifier = OutboxBacklogRecoveryVerifier()

    def test_item_is_correct(self):
        assert self.verifier.item == VerificationItem.OUTBOX

    def test_pass_with_default_config(self):
        config = make_config(parameters={})
        result = asyncio.run(self.verifier.execute(config))
        assert result.conclusion == VerificationConclusion.PASS

    def test_report_contains_verification_item(self):
        config = make_config(parameters={})
        result = asyncio.run(self.verifier.execute(config))
        assert result.report["verification_item"] == "V05_OUTBOX"
