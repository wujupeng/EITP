"""验证器测试基类。"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.application.prod.engine.iverifier import VerificationConfig, VerificationResult
from app.domain.prod.engine.enums import (
    VerificationConclusion,
    VerificationEnvironment,
    VerificationItem,
    ExecutorRole,
)
from uuid import uuid4


def make_config(**kwargs) -> VerificationConfig:
    return VerificationConfig(
        verification_item=kwargs.get("item", VerificationItem.BASELINE),
        tenant_id=uuid4(),
        environment="STAGING",
        parameters=kwargs.get("parameters", {}),
    )