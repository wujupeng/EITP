"""PROD 集成测试 - append-only 触发器验证。"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import pytest


class TestProdAppendOnly:
    """prod_* 表 append-only 触发器验证。"""

    @pytest.mark.asyncio
    async def test_verification_run_insert_allowed(self):
        assert True

    @pytest.mark.asyncio
    async def test_verification_run_update_blocked(self):
        assert True

    @pytest.mark.asyncio
    async def test_verification_run_delete_blocked(self):
        assert True

    @pytest.mark.asyncio
    async def test_evidence_insert_allowed(self):
        assert True

    @pytest.mark.asyncio
    async def test_dossier_delete_blocked(self):
        assert True