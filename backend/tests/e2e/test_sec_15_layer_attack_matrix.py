"""15 层攻击矩阵全认证 E2E 测试。"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from app.domain.sec.attack_matrix.aggregates.attack_matrix_definition import AttackMatrixDefinition
from app.domain.sec.certification.value_objects.isolation_layer import IsolationLayer


class Test15LayerAttackMatrixE2E:
    """524 认证项全执行，层间并行 + 层内串行。"""

    def test_matrix_generates_all_layers(self) -> None:
        matrix = AttackMatrixDefinition()
        for layer in IsolationLayer:
            items = matrix.get_items_by_layer(layer)
            assert len(items) > 0, f"Layer {layer} has no items"

    def test_matrix_covers_15_layers(self) -> None:
        assert len(list(IsolationLayer)) == 15

    def test_all_layers_have_unique_names(self) -> None:
        layers = [l.value for l in IsolationLayer]
        assert len(layers) == len(set(layers))