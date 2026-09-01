"""15 层 IsolationLayerExecutor 隔离层执行器 - 每层通过 HTTP 注入攻击向量并捕获隔离行为。"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from app.domain.sec.attack_matrix.value_objects.attack_vector import AttackVector
from app.domain.sec.certification.value_objects.evidence_snapshot import EvidenceSnapshot
from app.domain.sec.certification.value_objects.isolation_layer import (
    IsolationLayer,
    NineOperation,
)


@dataclass
class LayerExecutionResult:
    actual_behavior: str = ""
    evidence: EvidenceSnapshot | None = None
    duration_ms: float = 0.0
    is_reachable: bool = True
    error_detail: str = ""


class IsolationLayerExecutor(ABC):
    """隔离层执行器基类。"""

    layer: IsolationLayer

    @abstractmethod
    async def execute(self, vector: AttackVector, http_client: Any) -> LayerExecutionResult:
        ...

    def _build_evidence(
        self,
        request_log: dict[str, Any],
        response_log: dict[str, Any],
        sql_plan: str = "",
        rls_hits: list[dict[str, Any]] | None = None,
        redis_keys: list[str] | None = None,
        audit_records: list[dict[str, Any]] | None = None,
    ) -> EvidenceSnapshot:
        return EvidenceSnapshot(
            request_log=request_log,
            response_log=response_log,
            sql_plan=sql_plan,
            rls_hits=rls_hits or [],
            redis_keys=redis_keys or [],
            audit_records=audit_records or [],
            captured_at=datetime.now(timezone.utc),
        )


class JwtLayerExecutor(IsolationLayerExecutor):
    layer = IsolationLayer.JWT

    async def execute(self, vector: AttackVector, http_client: Any) -> LayerExecutionResult:
        start = datetime.now(timezone.utc)
        resp = await http_client.post(
            "/api/v1/mt/tenants/query",
            headers={"Authorization": "Bearer tampered_jwt_with_target_tenant"},
            json=vector.inject(),
        )
        duration = (datetime.now(timezone.utc) - start).total_seconds() * 1000
        return LayerExecutionResult(
            actual_behavior=f"http_{resp.status_code}",
            evidence=self._build_evidence(
                request_log={"url": "/api/v1/mt/tenants/query", "tampered_jwt": True},
                response_log={"status": resp.status_code, "body": resp.text},
            ),
            duration_ms=duration,
        )


class TenantTokenLayerExecutor(IsolationLayerExecutor):
    layer = IsolationLayer.TENANT_TOKEN

    async def execute(self, vector: AttackVector, http_client: Any) -> LayerExecutionResult:
        start = datetime.now(timezone.utc)
        resp = await http_client.get(
            "/api/v1/inv/balances",
            headers={"X-Tenant-Token": str(vector.target_tenant_id), "Authorization": "Bearer valid_jwt_attacker"},
        )
        duration = (datetime.now(timezone.utc) - start).total_seconds() * 1000
        return LayerExecutionResult(
            actual_behavior=f"http_{resp.status_code}",
            evidence=self._build_evidence(
                request_log={"x_tenant_token": str(vector.target_tenant_id)},
                response_log={"status": resp.status_code, "body": resp.text},
            ),
            duration_ms=duration,
        )


class TenantContextLayerExecutor(IsolationLayerExecutor):
    layer = IsolationLayer.TENANT_CONTEXT

    async def execute(self, vector: AttackVector, http_client: Any) -> LayerExecutionResult:
        start = datetime.now(timezone.utc)
        resp = await http_client.get("/api/v1/inv/balances", headers={"X-Tamper-Context": str(vector.target_tenant_id)})
        duration = (datetime.now(timezone.utc) - start).total_seconds() * 1000
        return LayerExecutionResult(
            actual_behavior=f"http_{resp.status_code}",
            evidence=self._build_evidence(
                request_log={"tampered_context": str(vector.target_tenant_id)},
                response_log={"status": resp.status_code, "body": resp.text},
            ),
            duration_ms=duration,
        )


class DataScopeLayerExecutor(IsolationLayerExecutor):
    layer = IsolationLayer.DATA_SCOPE

    async def execute(self, vector: AttackVector, http_client: Any) -> LayerExecutionResult:
        start = datetime.now(timezone.utc)
        resp = await http_client.get(f"/api/v1/inv/balances?tenant_id={vector.target_tenant_id}")
        duration = (datetime.now(timezone.utc) - start).total_seconds() * 1000
        return LayerExecutionResult(
            actual_behavior=f"http_{resp.status_code}",
            evidence=self._build_evidence(
                request_log={"query_tenant_id": str(vector.target_tenant_id)},
                response_log={"status": resp.status_code, "body": resp.text},
            ),
            duration_ms=duration,
        )


class ApiLayerExecutor(IsolationLayerExecutor):
    layer = IsolationLayer.API

    async def execute(self, vector: AttackVector, http_client: Any) -> LayerExecutionResult:
        start = datetime.now(timezone.utc)
        resp = await http_client.get(f"/api/v1/inv/balances/{vector.target_tenant_id}")
        duration = (datetime.now(timezone.utc) - start).total_seconds() * 1000
        return LayerExecutionResult(
            actual_behavior=f"http_{resp.status_code}",
            evidence=self._build_evidence(
                request_log={"url": f"/api/v1/inv/balances/{vector.target_tenant_id}"},
                response_log={"status": resp.status_code, "body": resp.text},
            ),
            duration_ms=duration,
        )


class ApplicationLayerExecutor(IsolationLayerExecutor):
    layer = IsolationLayer.APPLICATION

    async def execute(self, vector: AttackVector, http_client: Any) -> LayerExecutionResult:
        start = datetime.now(timezone.utc)
        resp = await http_client.post(
            "/api/v1/sal/orders",
            json={"target_tenant_id": str(vector.target_tenant_id), **vector.inject()},
        )
        duration = (datetime.now(timezone.utc) - start).total_seconds() * 1000
        return LayerExecutionResult(
            actual_behavior=f"http_{resp.status_code}",
            evidence=self._build_evidence(
                request_log={"target_tenant_id": str(vector.target_tenant_id)},
                response_log={"status": resp.status_code, "body": resp.text},
            ),
            duration_ms=duration,
        )


class RepositoryLayerExecutor(IsolationLayerExecutor):
    layer = IsolationLayer.REPOSITORY

    async def execute(self, vector: AttackVector, http_client: Any) -> LayerExecutionResult:
        start = datetime.now(timezone.utc)
        resp = await http_client.get("/api/v1/inv/balances?skip_tenant_filter=true")
        duration = (datetime.now(timezone.utc) - start).total_seconds() * 1000
        return LayerExecutionResult(
            actual_behavior=f"http_{resp.status_code}",
            evidence=self._build_evidence(
                request_log={"skip_tenant_filter": True},
                response_log={"status": resp.status_code, "body": resp.text},
            ),
            duration_ms=duration,
        )


class RlsLayerExecutor(IsolationLayerExecutor):
    layer = IsolationLayer.RLS

    async def execute(self, vector: AttackVector, http_client: Any) -> LayerExecutionResult:
        start = datetime.now(timezone.utc)
        resp = await http_client.post("/api/v1/sec/raw-sql", json={"sql": vector.payload.get("raw_sql", "")})
        duration = (datetime.now(timezone.utc) - start).total_seconds() * 1000
        return LayerExecutionResult(
            actual_behavior=f"http_{resp.status_code}",
            evidence=self._build_evidence(
                request_log={"raw_sql": vector.payload.get("raw_sql", "")},
                response_log={"status": resp.status_code, "body": resp.text},
                sql_plan="RLS bypass attempt",
            ),
            duration_ms=duration,
        )


class JoinLayerExecutor(IsolationLayerExecutor):
    layer = IsolationLayer.JOIN

    async def execute(self, vector: AttackVector, http_client: Any) -> LayerExecutionResult:
        start = datetime.now(timezone.utc)
        resp = await http_client.get(f"/api/v1/sec/join-test?target_tenant_id={vector.target_tenant_id}")
        duration = (datetime.now(timezone.utc) - start).total_seconds() * 1000
        return LayerExecutionResult(
            actual_behavior=f"http_{resp.status_code}",
            evidence=self._build_evidence(
                request_log={"join_target_tenant_id": str(vector.target_tenant_id)},
                response_log={"status": resp.status_code, "body": resp.text},
            ),
            duration_ms=duration,
        )


class AggregateLayerExecutor(IsolationLayerExecutor):
    layer = IsolationLayer.AGGREGATE

    async def execute(self, vector: AttackVector, http_client: Any) -> LayerExecutionResult:
        start = datetime.now(timezone.utc)
        resp = await http_client.get(f"/api/v1/sal/reports/aggregate?tenant_id={vector.target_tenant_id}")
        duration = (datetime.now(timezone.utc) - start).total_seconds() * 1000
        return LayerExecutionResult(
            actual_behavior=f"http_{resp.status_code}",
            evidence=self._build_evidence(
                request_log={"aggregate_tenant_id": str(vector.target_tenant_id)},
                response_log={"status": resp.status_code, "body": resp.text},
            ),
            duration_ms=duration,
        )


class AuditLayerExecutor(IsolationLayerExecutor):
    layer = IsolationLayer.AUDIT

    async def execute(self, vector: AttackVector, http_client: Any) -> LayerExecutionResult:
        start = datetime.now(timezone.utc)
        resp = await http_client.get(f"/api/v1/mt/audit-logs?tenant_id={vector.target_tenant_id}")
        duration = (datetime.now(timezone.utc) - start).total_seconds() * 1000
        return LayerExecutionResult(
            actual_behavior=f"http_{resp.status_code}",
            evidence=self._build_evidence(
                request_log={"audit_tenant_id": str(vector.target_tenant_id)},
                response_log={"status": resp.status_code, "body": resp.text},
            ),
            duration_ms=duration,
        )


class ExportLayerExecutor(IsolationLayerExecutor):
    layer = IsolationLayer.EXPORT

    async def execute(self, vector: AttackVector, http_client: Any) -> LayerExecutionResult:
        start = datetime.now(timezone.utc)
        resp = await http_client.get(f"/api/v1/sal/export?tenant_id={vector.target_tenant_id}")
        duration = (datetime.now(timezone.utc) - start).total_seconds() * 1000
        return LayerExecutionResult(
            actual_behavior=f"http_{resp.status_code}",
            evidence=self._build_evidence(
                request_log={"export_tenant_id": str(vector.target_tenant_id)},
                response_log={"status": resp.status_code, "body": resp.text},
            ),
            duration_ms=duration,
        )


class CacheLayerExecutor(IsolationLayerExecutor):
    layer = IsolationLayer.CACHE

    async def execute(self, vector: AttackVector, http_client: Any) -> LayerExecutionResult:
        start = datetime.now(timezone.utc)
        resp = await http_client.get("/api/v1/sec/redis-scan")
        duration = (datetime.now(timezone.utc) - start).total_seconds() * 1000
        keys_in_response = resp.json().get("keys", []) if resp.status_code == 200 else []
        violating_keys = [k for k in keys_in_response if not k.startswith(f"eitp:{vector.attacker_tenant_id}:")]
        return LayerExecutionResult(
            actual_behavior=f"violating_keys_{len(violating_keys)}",
            evidence=self._build_evidence(
                request_log={"scan": True},
                response_log={"status": resp.status_code, "violating_keys": violating_keys},
                redis_keys=keys_in_response,
            ),
            duration_ms=duration,
        )


class AsyncJobLayerExecutor(IsolationLayerExecutor):
    layer = IsolationLayer.ASYNC_JOB

    async def execute(self, vector: AttackVector, http_client: Any) -> LayerExecutionResult:
        start = datetime.now(timezone.utc)
        resp = await http_client.post(
            "/api/v1/sec/async-job-test",
            json={"target_tenant_id": str(vector.target_tenant_id)},
        )
        duration = (datetime.now(timezone.utc) - start).total_seconds() * 1000
        return LayerExecutionResult(
            actual_behavior=f"http_{resp.status_code}",
            evidence=self._build_evidence(
                request_log={"async_target_tenant_id": str(vector.target_tenant_id)},
                response_log={"status": resp.status_code, "body": resp.text},
            ),
            duration_ms=duration,
        )


class E2ELayerExecutor(IsolationLayerExecutor):
    layer = IsolationLayer.E2E

    async def execute(self, vector: AttackVector, http_client: Any) -> LayerExecutionResult:
        start = datetime.now(timezone.utc)
        resp = await http_client.post("/api/v1/sec/attack-chain", json=vector.inject())
        duration = (datetime.now(timezone.utc) - start).total_seconds() * 1000
        return LayerExecutionResult(
            actual_behavior=f"http_{resp.status_code}",
            evidence=self._build_evidence(
                request_log={"attack_chain": "14_step"},
                response_log={"status": resp.status_code, "body": resp.text},
            ),
            duration_ms=duration,
        )


LAYER_EXECUTOR_MAP: dict[IsolationLayer, type[IsolationLayerExecutor]] = {
    IsolationLayer.JWT: JwtLayerExecutor,
    IsolationLayer.TENANT_TOKEN: TenantTokenLayerExecutor,
    IsolationLayer.TENANT_CONTEXT: TenantContextLayerExecutor,
    IsolationLayer.DATA_SCOPE: DataScopeLayerExecutor,
    IsolationLayer.API: ApiLayerExecutor,
    IsolationLayer.APPLICATION: ApplicationLayerExecutor,
    IsolationLayer.REPOSITORY: RepositoryLayerExecutor,
    IsolationLayer.RLS: RlsLayerExecutor,
    IsolationLayer.JOIN: JoinLayerExecutor,
    IsolationLayer.AGGREGATE: AggregateLayerExecutor,
    IsolationLayer.AUDIT: AuditLayerExecutor,
    IsolationLayer.EXPORT: ExportLayerExecutor,
    IsolationLayer.CACHE: CacheLayerExecutor,
    IsolationLayer.ASYNC_JOB: AsyncJobLayerExecutor,
    IsolationLayer.E2E: E2ELayerExecutor,
}


def get_executor(layer: IsolationLayer) -> IsolationLayerExecutor:
    cls = LAYER_EXECUTOR_MAP[layer]
    return cls()