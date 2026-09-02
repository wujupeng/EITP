"""EITP-SEC-001 AttackMatrixDefinition 聚合根单元测试。

覆盖攻击矩阵定义：15 层 × 9 操作 × 55 聚合根 = 7425 矩阵项，
加上 15 个 E2E-attack_chain 与 14 个 E2E-step，总计 7454 个认证项 ID。

注：需求描述中的 "524" 实为 CertificationIssuer 的签发门槛 (_REQUIRED_TOTAL_ITEMS)，
AttackMatrixDefinition 实际生成 7454 个 item id，本测试以代码真实行为为准。
"""

from __future__ import annotations

import re
from uuid import UUID

import pytest

from app.domain.sec.attack_matrix.aggregates.attack_matrix_definition import (
    AttackMatrixDefinition,
    _AGGREGATE_ROOTS,
)
from app.domain.sec.certification.value_objects.isolation_layer import (
    IsolationLayer,
    NineOperation,
)


@pytest.fixture
def matrix() -> AttackMatrixDefinition:
    return AttackMatrixDefinition()


class AttackMatrixDefinitionTest:
    """AttackMatrixDefinition 聚合根行为验证。"""

    def test_layers_count_is_15(self, matrix: AttackMatrixDefinition) -> None:
        assert len(matrix.layers) == 15
        assert matrix.layers == list(IsolationLayer)

    def test_operations_count_is_9(self, matrix: AttackMatrixDefinition) -> None:
        assert len(matrix.operations) == 9
        assert matrix.operations == list(NineOperation)

    def test_total_aggregate_roots_is_55(self, matrix: AttackMatrixDefinition) -> None:
        assert matrix.total_aggregate_roots == 55
        # 按模块明细校验
        expected = {"MT": 4, "IAM": 6, "INV": 4, "MDM": 9, "WMS": 13, "PUR": 7, "SAL": 12}
        for module, count in expected.items():
            assert len(_AGGREGATE_ROOTS[module]) == count, f"module {module} root count mismatch"
        assert sum(expected.values()) == 55

    def test_total_matrix_items_is_7425(self, matrix: AttackMatrixDefinition) -> None:
        # 15 * 9 * 55 = 7425
        assert matrix.total_matrix_items == 7425
        assert matrix.total_matrix_items == 15 * 9 * 55

    def test_total_items_is_7454(self, matrix: AttackMatrixDefinition) -> None:
        # 7425 matrix + 15 layer E2E-attack_chain + 14 e2e_steps = 7454
        assert matrix.total_items == 7454
        assert matrix.total_items == matrix.total_matrix_items + len(matrix.layers) + matrix.e2e_steps

    def test_e2e_steps_is_14(self, matrix: AttackMatrixDefinition) -> None:
        assert matrix.e2e_steps == 14

    def test_generate_item_ids_count_matches_total_items(self, matrix: AttackMatrixDefinition) -> None:
        item_ids = matrix.generate_item_ids()
        assert len(item_ids) == matrix.total_items == 7454

    def test_generate_item_ids_are_unique(self, matrix: AttackMatrixDefinition) -> None:
        item_ids = matrix.generate_item_ids()
        assert len(set(item_ids)) == len(item_ids)

    def test_matrix_item_id_format_layer_operation_module_root(self, matrix: AttackMatrixDefinition) -> None:
        """矩阵项 ID 格式: SEC-ITEM-{layer}-{operation}-{module}:{root}。"""
        item_ids = matrix.generate_item_ids()
        pattern = re.compile(r"^SEC-ITEM-[a-z0-9_]+-[a-z0-9_]+-[A-Z]+:[A-Za-z]+$")
        matrix_ids = [
            iid for iid in item_ids
            if not iid.startswith("SEC-ITEM-E2E-") and "E2E-attack_chain" not in iid
        ]
        assert len(matrix_ids) == 7425
        for iid in matrix_ids:
            assert pattern.match(iid), f"matrix item id format invalid: {iid}"

    def test_layer_e2e_attack_chain_id_format(self, matrix: AttackMatrixDefinition) -> None:
        item_ids = matrix.generate_item_ids()
        layer_e2e = [iid for iid in item_ids if iid.endswith("-E2E-attack_chain")]
        assert len(layer_e2e) == 15
        for iid in layer_e2e:
            assert re.match(r"^SEC-ITEM-[a-z0-9_]+-E2E-attack_chain$", iid), iid

    def test_e2e_step_id_format(self, matrix: AttackMatrixDefinition) -> None:
        item_ids = matrix.generate_item_ids()
        steps = [iid for iid in item_ids if iid.startswith("SEC-ITEM-E2E-step-")]
        assert len(steps) == 14
        for idx, iid in enumerate(steps, start=1):
            assert iid == f"SEC-ITEM-E2E-step-{idx:02d}", iid

    def test_generate_item_ids_ordering(self, matrix: AttackMatrixDefinition) -> None:
        """顺序: 15 层 E2E-attack_chain → 7425 矩阵项 → 14 E2E-step。"""
        item_ids = matrix.generate_item_ids()
        # 前 15 个为 layer E2E-attack_chain
        for iid in item_ids[:15]:
            assert iid.endswith("-E2E-attack_chain")
        # 接下来 7425 个为矩阵项
        for iid in item_ids[15:15 + 7425]:
            assert "E2E-attack_chain" not in iid
            assert not iid.startswith("SEC-ITEM-E2E-step-")
        # 最后 14 个为 E2E-step
        for iid in item_ids[15 + 7425:]:
            assert iid.startswith("SEC-ITEM-E2E-step-")

    def test_get_items_by_layer_returns_layer_items(self, matrix: AttackMatrixDefinition) -> None:
        # get_items_by_layer 用精确前缀匹配 "SEC-ITEM-{layer}-"，不跨层匹配同名操作项。
        for layer in IsolationLayer:
            items = matrix.get_items_by_layer(layer)
            prefix = f"SEC-ITEM-{layer.value}-"
            expected = [iid for iid in matrix.generate_item_ids() if iid.startswith(prefix)]
            assert items == expected, f"layer {layer.value} filter logic mismatch"
            assert len(items) > 0
            for iid in items:
                assert iid.startswith(prefix), iid

    def test_get_items_by_layer_all_layers_return_496(self, matrix: AttackMatrixDefinition) -> None:
        # 精确前缀匹配后，所有层均返回 1 个 E2E-attack_chain + 9*55 矩阵项 = 496
        for layer in IsolationLayer:
            assert len(matrix.get_items_by_layer(layer)) == 496, f"layer {layer.value}"

    def test_get_items_by_module_returns_module_items(self, matrix: AttackMatrixDefinition) -> None:
        for module, roots in _AGGREGATE_ROOTS.items():
            items = matrix.get_items_by_module(module)
            # 每模块: 15 层 * 9 操作 * len(roots)
            expected = 15 * 9 * len(roots)
            assert len(items) == expected, f"module {module}: expected {expected}, got {len(items)}"
            for iid in items:
                assert f"-{module}:" in iid, iid

    def test_default_matrix_version(self, matrix: AttackMatrixDefinition) -> None:
        assert matrix.matrix_version == "1.0"

    def test_default_matrix_id_is_uuid(self, matrix: AttackMatrixDefinition) -> None:
        assert isinstance(matrix.matrix_id, UUID)

    def test_aggregate_roots_dict_per_instance(self) -> None:
        # default_factory=lambda: copy.deepcopy(_AGGREGATE_ROOTS) 产出独立 dict (深拷贝)，
        # 两个实例的 aggregate_roots 是不同 dict 对象，且内部 list 也独立。
        m1 = AttackMatrixDefinition()
        m2 = AttackMatrixDefinition()
        assert m1.aggregate_roots is not m2.aggregate_roots
        assert m1.aggregate_roots == m2.aggregate_roots
        m1.aggregate_roots["MT"].append("NewAggregate")
        assert "NewAggregate" not in m2.aggregate_roots["MT"]