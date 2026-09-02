"""PROD 集成测试 - 故障注入环境守卫。"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import pytest
from app.application.prod.tools.fault_injector import FaultInjector
from app.application.prod.tools.injectors.connection_pool_exhaustion_injector import ConnectionPoolExhaustionInjector
from app.domain.prod.engine.enums import VerificationEnvironment
from app.domain.prod.exceptions import PRODError


class TestProdFaultInjectionEnvGuard:
    """故障注入环境守卫，禁止 PROD。"""

    def test_staging_allowed(self):
        injector = ConnectionPoolExhaustionInjector(VerificationEnvironment.STAGING)
        assert injector._environment == VerificationEnvironment.STAGING

    def test_pre_prod_allowed(self):
        injector = ConnectionPoolExhaustionInjector(VerificationEnvironment.PRE_PROD)
        assert injector._environment == VerificationEnvironment.PRE_PROD

    def test_prod_forbidden(self):
        from enum import Enum
        class FakeProdEnv(str, Enum):
            PROD = "PROD"
        with pytest.raises(PRODError):
            ConnectionPoolExhaustionInjector(FakeProdEnv.PROD)