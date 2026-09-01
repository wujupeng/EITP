"""AttackVectorFactory 领域服务 - 15 层攻击向量构造工厂。"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from app.domain.sec.attack_matrix.value_objects.attack_vector import AttackVector
from app.domain.sec.certification.value_objects.isolation_layer import (
    IsolationLayer,
    NineOperation,
)


class AttackVectorFactory:
    """按 15 层各构造对应攻击向量。"""

    @staticmethod
    def create(
        layer: IsolationLayer,
        operation: NineOperation,
        attacker_tenant_id: UUID,
        target_tenant_id: UUID,
        aggregate_root: str = "",
    ) -> AttackVector:
        builder = _LAYER_BUILDERS.get(layer)
        if builder is None:
            raise ValueError(f"No builder for layer {layer}")
        payload = builder(attacker_tenant_id, target_tenant_id, operation, aggregate_root)
        return AttackVector(
            attacker_tenant_id=attacker_tenant_id,
            target_tenant_id=target_tenant_id,
            operation=operation,
            layer=layer,
            payload=payload,
        )

    @staticmethod
    def create_all_layers(
        operation: NineOperation,
        attacker_tenant_id: UUID,
        target_tenant_id: UUID,
        aggregate_root: str = "",
    ) -> list[AttackVector]:
        return [
            AttackVectorFactory.create(layer, operation, attacker_tenant_id, target_tenant_id, aggregate_root)
            for layer in IsolationLayer
        ]


def _jwt_payload(att: UUID, tgt: UUID, op: NineOperation, ar: str) -> dict[str, Any]:
    return {"attack": "jwt_tenant_id_tamper", "tampered_tenant_id": str(tgt), "operation": op.value, "aggregate_root": ar}

def _tenant_token_payload(att: UUID, tgt: UUID, op: NineOperation, ar: str) -> dict[str, Any]:
    return {"attack": "x_tenant_token_forgery", "forged_tenant_id": str(tgt), "operation": op.value, "aggregate_root": ar}

def _tenant_context_payload(att: UUID, tgt: UUID, op: NineOperation, ar: str) -> dict[str, Any]:
    return {"attack": "context_tenant_id_tamper", "tampered_tenant_id": str(tgt), "operation": op.value, "aggregate_root": ar}

def _data_scope_payload(att: UUID, tgt: UUID, op: NineOperation, ar: str) -> dict[str, Any]:
    return {"attack": "datascope_bypass", "requested_tenant_id": str(tgt), "operation": op.value, "aggregate_root": ar}

def _api_payload(att: UUID, tgt: UUID, op: NineOperation, ar: str) -> dict[str, Any]:
    return {"attack": "api_cross_tenant_resource_id", "target_resource_tenant_id": str(tgt), "operation": op.value, "aggregate_root": ar}

def _application_payload(att: UUID, tgt: UUID, op: NineOperation, ar: str) -> dict[str, Any]:
    return {"attack": "app_target_tenant_id_tamper", "tampered_target_tenant_id": str(tgt), "operation": op.value, "aggregate_root": ar}

def _repository_payload(att: UUID, tgt: UUID, op: NineOperation, ar: str) -> dict[str, Any]:
    return {"attack": "repo_disable_tenant_filter", "operation": op.value, "aggregate_root": ar}

def _rls_payload(att: UUID, tgt: UUID, op: NineOperation, ar: str) -> dict[str, Any]:
    return {"attack": "rls_direct_sql_bypass", "raw_sql": f"SELECT * FROM {ar} WHERE tenant_id = '{tgt}'", "operation": op.value, "aggregate_root": ar}

def _join_payload(att: UUID, tgt: UUID, op: NineOperation, ar: str) -> dict[str, Any]:
    return {"attack": "join_cross_tenant_leak", "join_target_tenant_id": str(tgt), "operation": op.value, "aggregate_root": ar}

def _aggregate_payload(att: UUID, tgt: UUID, op: NineOperation, ar: str) -> dict[str, Any]:
    return {"attack": "aggregate_cross_tenant", "target_tenant_id": str(tgt), "operation": op.value, "aggregate_root": ar}

def _audit_payload(att: UUID, tgt: UUID, op: NineOperation, ar: str) -> dict[str, Any]:
    return {"attack": "audit_cross_tenant_query", "target_tenant_id": str(tgt), "operation": op.value, "aggregate_root": ar}

def _export_payload(att: UUID, tgt: UUID, op: NineOperation, ar: str) -> dict[str, Any]:
    return {"attack": "export_cross_tenant", "target_tenant_id": str(tgt), "operation": op.value, "aggregate_root": ar}

def _cache_payload(att: UUID, tgt: UUID, op: NineOperation, ar: str) -> dict[str, Any]:
    return {"attack": "cache_scan_key_prefix", "expected_prefix": f"eitp:{att}:*", "operation": op.value, "aggregate_root": ar}

def _async_job_payload(att: UUID, tgt: UUID, op: NineOperation, ar: str) -> dict[str, Any]:
    return {"attack": "async_job_cross_tenant", "target_tenant_id": str(tgt), "operation": op.value, "aggregate_root": ar}

def _e2e_payload(att: UUID, tgt: UUID, op: NineOperation, ar: str) -> dict[str, Any]:
    return {"attack": "e2e_14_step_attack_chain", "target_tenant_id": str(tgt), "operation": op.value, "aggregate_root": ar}


_LAYER_BUILDERS: dict[IsolationLayer, Any] = {
    IsolationLayer.JWT: _jwt_payload,
    IsolationLayer.TENANT_TOKEN: _tenant_token_payload,
    IsolationLayer.TENANT_CONTEXT: _tenant_context_payload,
    IsolationLayer.DATA_SCOPE: _data_scope_payload,
    IsolationLayer.API: _api_payload,
    IsolationLayer.APPLICATION: _application_payload,
    IsolationLayer.REPOSITORY: _repository_payload,
    IsolationLayer.RLS: _rls_payload,
    IsolationLayer.JOIN: _join_payload,
    IsolationLayer.AGGREGATE: _aggregate_payload,
    IsolationLayer.AUDIT: _audit_payload,
    IsolationLayer.EXPORT: _export_payload,
    IsolationLayer.CACHE: _cache_payload,
    IsolationLayer.ASYNC_JOB: _async_job_payload,
    IsolationLayer.E2E: _e2e_payload,
}