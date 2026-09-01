"""EITP-SEC-001 AttackVectorFactory 与 AttackVector 值对象单元测试。

覆盖 15 层攻击向量构造、不可变性、payload 差异化与全层批量构造。
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from uuid import uuid4

import pytest

from app.domain.sec.attack_matrix.services.attack_vector_factory import (
    AttackVectorFactory,
    _LAYER_BUILDERS,
)
from app.domain.sec.attack_matrix.value_objects.attack_vector import AttackVector
from app.domain.sec.certification.value_objects.isolation_layer import (
    IsolationLayer,
    NineOperation,
)


@pytest.fixture
def attacker_id() -> object:
    return uuid4()


@pytest.fixture
def target_id() -> object:
    return uuid4()


class AttackVectorTest:
    """AttackVector 值对象不可变性与 inject 行为。"""

    def test_frozen_dataclass_immutable(self, attacker_id: object, target_id: object) -> None:
        av = AttackVector(
            attacker_tenant_id=attacker_id,
            target_tenant_id=target_id,
            operation=NineOperation.SELECT,
            layer=IsolationLayer.JWT,
            payload={"k": "v"},
        )
        with pytest.raises(FrozenInstanceError):
            av.layer = IsolationLayer.API  # type: ignore[misc]

    def test_inject_returns_stringified_dict(self, attacker_id: object, target_id: object) -> None:
        av = AttackVector(
            attacker_tenant_id=attacker_id,
            target_tenant_id=target_id,
            operation=NineOperation.SELECT,
            layer=IsolationLayer.JWT,
            payload={"attack": "jwt_tenant_id_tamper"},
        )
        injected = av.inject()
        assert injected["attacker_tenant_id"] == str(attacker_id)
        assert injected["target_tenant_id"] == str(target_id)
        assert injected["operation"] == "select"
        assert injected["layer"] == "jwt"
        assert injected["payload"] == {"attack": "jwt_tenant_id_tamper"}

    def test_default_payload_is_empty_dict(self, attacker_id: object, target_id: object) -> None:
        av = AttackVector(
            attacker_tenant_id=attacker_id,
            target_tenant_id=target_id,
            operation=NineOperation.SELECT,
            layer=IsolationLayer.JWT,
        )
        assert av.payload == {}

    def test_equality_by_value(self, attacker_id: object, target_id: object) -> None:
        av1 = AttackVector(attacker_id, target_id, NineOperation.SELECT, IsolationLayer.JWT, {"a": 1})
        av2 = AttackVector(attacker_id, target_id, NineOperation.SELECT, IsolationLayer.JWT, {"a": 1})
        assert av1 == av2


class AttackVectorFactoryTest:
    """AttackVectorFactory 15 层构造行为。"""

    def test_create_returns_attack_vector_with_correct_metadata(
        self, attacker_id: object, target_id: object
    ) -> None:
        av = AttackVectorFactory.create(
            IsolationLayer.JWT, NineOperation.SELECT, attacker_id, target_id, "User"
        )
        assert isinstance(av, AttackVector)
        assert av.attacker_tenant_id == attacker_id
        assert av.target_tenant_id == target_id
        assert av.layer == IsolationLayer.JWT
        assert av.operation == NineOperation.SELECT

    def test_create_all_15_layers_have_distinct_payload_attacks(
        self, attacker_id: object, target_id: object
    ) -> None:
        vectors = AttackVectorFactory.create_all_layers(
            NineOperation.SELECT, attacker_id, target_id, "User"
        )
        assert len(vectors) == 15
        assert {v.layer for v in vectors} == set(IsolationLayer)
        attacks = [v.payload["attack"] for v in vectors]
        assert len(set(attacks)) == 15, "每层 payload attack 标识应唯一"

    @pytest.mark.parametrize("layer", list(IsolationLayer))
    def test_each_layer_payload_contains_attack_key(
        self, layer: IsolationLayer, attacker_id: object, target_id: object
    ) -> None:
        av = AttackVectorFactory.create(
            layer, NineOperation.UPDATE, attacker_id, target_id, "Tenant"
        )
        assert "attack" in av.payload
        assert av.payload["operation"] == "update"
        assert av.payload["aggregate_root"] == "Tenant"

    def test_jwt_payload_tampered_tenant_id(self, attacker_id: object, target_id: object) -> None:
        av = AttackVectorFactory.create(
            IsolationLayer.JWT, NineOperation.SELECT, attacker_id, target_id, "User"
        )
        assert av.payload["attack"] == "jwt_tenant_id_tamper"
        assert av.payload["tampered_tenant_id"] == str(target_id)

    def test_rls_payload_contains_raw_sql(self, attacker_id: object, target_id: object) -> None:
        av = AttackVectorFactory.create(
            IsolationLayer.RLS, NineOperation.SELECT, attacker_id, target_id, "InventoryBalance"
        )
        assert av.payload["attack"] == "rls_direct_sql_bypass"
        assert "SELECT * FROM InventoryBalance" in av.payload["raw_sql"]
        assert str(target_id) in av.payload["raw_sql"]

    def test_cache_payload_expected_prefix(self, attacker_id: object, target_id: object) -> None:
        av = AttackVectorFactory.create(
            IsolationLayer.CACHE, NineOperation.SELECT,
            attacker_id, target_id, "Tenant",
        )
        assert av.payload["attack"] == "cache_scan_key_prefix"
        assert av.payload["expected_prefix"] == f"eitp:{attacker_id}:*"

    def test_repository_payload_disables_tenant_filter(self, attacker_id: object, target_id: object) -> None:
        av = AttackVectorFactory.create(
            IsolationLayer.REPOSITORY, NineOperation.DELETE, attacker_id, target_id, "User"
        )
        assert av.payload["attack"] == "repo_disable_tenant_filter"

    def test_layer_builders_cover_all_15_layers(self) -> None:
        assert set(_LAYER_BUILDERS.keys()) == set(IsolationLayer)
        assert len(_LAYER_BUILDERS) == 15

    def test_create_propagates_aggregate_root_into_payload(
        self, attacker_id: object, target_id: object
    ) -> None:
        av = AttackVectorFactory.create(
            IsolationLayer.AGGREGATE, NineOperation.AGGREGATE, attacker_id, target_id, "SalesOrder"
        )
        assert av.payload["aggregate_root"] == "SalesOrder"
        assert av.payload["target_tenant_id"] == str(target_id)

    def test_create_with_empty_aggregate_root_default(
        self, attacker_id: object, target_id: object
    ) -> None:
        av = AttackVectorFactory.create(
            IsolationLayer.AUDIT, NineOperation.AUDIT, attacker_id, target_id
        )
        assert av.payload["aggregate_root"] == ""