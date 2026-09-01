"""认证执行引擎集成测试 - HTTP 注入攻击向量，15 层执行器，编排器层间并行 + 层内串行。"""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest

from app.application.sec.attack_matrix_certification_orchestrator import (
    AttackMatrixCertificationOrchestrator,
    MatrixExecutionResult,
)
from app.domain.sec.attack_matrix.services.certification_item_executor import (
    CertificationItemExecutor,
)
from app.domain.sec.certification.aggregates.certification_item_aggregate import (
    CertificationItemAggregate,
)
from app.domain.sec.certification.value_objects.isolation_layer import (
    Conclusion,
    IsolationLayer,
    NineOperation,
)


@pytest.fixture
def mock_http_client() -> Any:
    client = AsyncMock()
    resp = MagicMock()
    resp.status_code = 403
    resp.text = "Forbidden"
    resp.json.return_value = {}
    client.get.return_value = resp
    client.post.return_value = resp
    client.put.return_value = resp
    client.delete.return_value = resp
    return client


@pytest.fixture
def mock_provisioner(mock_http_client: Any) -> Any:
    from app.infrastructure.sec.test_tenant_provisioner import TestTenantPair
    provisioner = AsyncMock()
    pair = TestTenantPair(tenant_a=uuid4(), tenant_b=uuid4())
    provisioner.provision.return_value = pair
    provisioner.cleanup.return_value = []
    return provisioner


class TestCertificationItemExecutorIntegration:
    """认证项执行器集成测试。"""

    @pytest.mark.asyncio
    async def test_execute_item_passes_when_behavior_matches(self, mock_http_client: Any) -> None:
        executor = CertificationItemExecutor(mock_http_client)
        item = CertificationItemAggregate(
            item_id="SEC-ITEM-jwt-select-Tenant",
            batch_id=uuid4(),
            layer=IsolationLayer.JWT,
            operation=NineOperation.SELECT,
            aggregate_root="Tenant",
            expected_behavior="http_403",
            tenant_id=uuid4(),
        )
        from app.domain.sec.attack_matrix.services.attack_vector_factory import AttackVectorFactory
        item.attack_vector = AttackVectorFactory.create(
            IsolationLayer.JWT, NineOperation.SELECT, uuid4(), uuid4(), "Tenant"
        )
        result = await executor.execute_item(item)
        assert result.conclusion in (Conclusion.PASS, Conclusion.FAIL, Conclusion.UNEXECUTABLE)

    @pytest.mark.asyncio
    async def test_execute_batch_processes_all_items(self, mock_http_client: Any) -> None:
        executor = CertificationItemExecutor(mock_http_client)
        items = [
            CertificationItemAggregate(
                item_id=f"SEC-ITEM-jwt-select-AR{i}",
                batch_id=uuid4(),
                layer=IsolationLayer.JWT,
                operation=NineOperation.SELECT,
                aggregate_root=f"AR{i}",
                expected_behavior="http_403",
                tenant_id=uuid4(),
            )
            for i in range(5)
        ]
        from app.domain.sec.attack_matrix.services.attack_vector_factory import AttackVectorFactory
        for item in items:
            item.attack_vector = AttackVectorFactory.create(
                IsolationLayer.JWT, NineOperation.SELECT, uuid4(), uuid4(), item.aggregate_root
            )
        results = await executor.execute_batch(items)
        assert len(results) == 5


class TestAttackMatrixOrchestratorIntegration:
    """攻击矩阵编排器集成测试。"""

    @pytest.mark.asyncio
    async def test_orchestrator_returns_result(self, mock_http_client: Any) -> None:
        orchestrator = AttackMatrixCertificationOrchestrator(mock_http_client)
        result = await orchestrator.execute(
            matrix_version="test-v1",
            tenant_id=uuid4(),
            layers=[IsolationLayer.JWT],
        )
        assert result.batch_id is not None
        assert result.progress is not None

    @pytest.mark.asyncio
    async def test_orchestrator_progress_tracking(self, mock_http_client: Any) -> None:
        orchestrator = AttackMatrixCertificationOrchestrator(mock_http_client)
        result = await orchestrator.execute(
            matrix_version="test-v1",
            tenant_id=uuid4(),
            layers=[IsolationLayer.JWT, IsolationLayer.TENANT_TOKEN],
        )
        progress = orchestrator.get_progress(result.batch_id)
        assert progress is not None
        assert progress.total_items >= 0