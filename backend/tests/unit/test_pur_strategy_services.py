"""PUR 策略领域服务单元测试 - 审批路由 + WMS/INV 映射器 + 三边对账。

覆盖 ApprovalRouterService 金额阈值路由（≤10000→L1, ≤100000→L2, >100000→L3）边界、
PurToWmsReceivingMapper/PurToInvFinancialMapper 参数构建（红线：采购不直接改库存/成本）、
PurReconcileService 三边对账一致/不一致与浮点精度。
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.domain.purchasing.services.pur_strategy_services import (
    ApprovalRule,
    ApprovalRouterService,
    PurReconcileService,
    PurToInvFinancialMapper,
    PurToWmsReceivingMapper,
)
from app.interfaces.middleware.error_handler import PURError, PURErrorCode


class ApprovalRouterServiceTest:
    """ApprovalRouterService 金额阈值审批路由测试。"""

    def test_default_thresholds_l1_l2_l3(self) -> None:
        router = ApprovalRouterService()
        assert router.route(0) == "pur:approver_l1"
        assert router.route(10000) == "pur:approver_l1"
        assert router.route(10000.01) == "pur:approver_l2"
        assert router.route(100000) == "pur:approver_l2"
        assert router.route(100000.01) == "pur:approver_l3"
        assert router.route(9999999) == "pur:approver_l3"

    def test_boundary_exactly_10000_routes_l1(self) -> None:
        router = ApprovalRouterService()
        assert router.route(10000) == "pur:approver_l1"

    def test_boundary_exactly_100000_routes_l2(self) -> None:
        router = ApprovalRouterService()
        assert router.route(100000) == "pur:approver_l2"

    def test_negative_amount_routes_l1(self) -> None:
        router = ApprovalRouterService()
        assert router.route(-1) == "pur:approver_l1"

    def test_custom_rules_sorted_by_threshold(self) -> None:
        rules = [
            ApprovalRule(threshold=500, approver_role="r_low"),
            ApprovalRule(threshold=50, approver_role="r_min"),
            ApprovalRule(threshold=float("inf"), approver_role="r_high"),
        ]
        router = ApprovalRouterService(rules)
        assert router.route(10) == "r_min"
        assert router.route(50) == "r_min"
        assert router.route(100) == "r_low"
        assert router.route(500) == "r_low"
        assert router.route(501) == "r_high"

    def test_empty_rules_falls_back_to_defaults(self) -> None:
        router = ApprovalRouterService(rules=None)
        assert router.route(1) == "pur:approver_l1"

    def test_single_rule_routes_all_amounts(self) -> None:
        router = ApprovalRouterService(rules=[ApprovalRule(threshold=1000, approver_role="only")])
        assert router.route(500) == "only"
        assert router.route(1000) == "only"
        # 超过唯一阈值 → 兜底返回最后一条规则
        assert router.route(2000) == "only"


class PurToWmsReceivingMapperTest:
    """PurToWmsReceivingMapper 参数构建测试 - 第一条红线：采购不直接改库存。"""

    def test_build_wms_receiving_params_full_mapping(self) -> None:
        tenant_id = uuid4()
        order_id = uuid4()
        wh_id = uuid4()
        zone_id = uuid4()
        sku_id = uuid4()
        loc_id = uuid4()
        op_id = uuid4()
        params = PurToWmsReceivingMapper.build_wms_receiving_params(
            tenant_id, order_id, wh_id, zone_id, sku_id, 100.0, loc_id, op_id,
        )
        assert params["tenant_id"] == str(tenant_id)
        assert params["source_document_id"] == str(order_id)
        assert params["source_document_type"] == "purchase_order"
        assert params["warehouse_id"] == str(wh_id)
        assert params["zone_id"] == str(zone_id)
        assert params["sku_id"] == str(sku_id)
        assert params["quantity"] == 100.0
        assert params["location_id"] == str(loc_id)
        assert params["operated_by"] == str(op_id)

    def test_build_wms_receiving_params_uuids_converted_to_str(self) -> None:
        params = PurToWmsReceivingMapper.build_wms_receiving_params(
            uuid4(), uuid4(), uuid4(), uuid4(), uuid4(), 1, uuid4(), uuid4(),
        )
        for key in ("tenant_id", "source_document_id", "warehouse_id", "zone_id",
                    "sku_id", "location_id", "operated_by"):
            assert isinstance(params[key], str)

    def test_build_wms_receiving_params_quantity_preserved_as_number(self) -> None:
        params = PurToWmsReceivingMapper.build_wms_receiving_params(
            uuid4(), uuid4(), uuid4(), uuid4(), uuid4(), 12.5, uuid4(), uuid4(),
        )
        assert params["quantity"] == 12.5
        assert not isinstance(params["quantity"], str)


class PurToInvFinancialMapperTest:
    """PurToInvFinancialMapper 参数构建测试 - 第二条红线：采购不直接改成本。"""

    def test_build_inv_cost_params_full_mapping(self) -> None:
        tenant_id = uuid4()
        sku_id = uuid4()
        wh_id = uuid4()
        doc_id = uuid4()
        op_id = uuid4()
        params = PurToInvFinancialMapper.build_inv_cost_params(
            tenant_id, sku_id, wh_id, 50.0, 20.0, doc_id, op_id,
        )
        assert params["tenant_id"] == str(tenant_id)
        assert params["sku_id"] == str(sku_id)
        assert params["warehouse_id"] == str(wh_id)
        assert params["quantity"] == 50.0
        assert params["unit_cost"] == 20.0
        assert params["document_id"] == str(doc_id)
        assert params["document_type"] == "purchase_settlement"
        assert params["operated_by"] == str(op_id)

    def test_build_inv_return_params_marks_return_out(self) -> None:
        params = PurToInvFinancialMapper.build_inv_return_params(
            uuid4(), uuid4(), uuid4(), 5.0, uuid4(), uuid4(),
        )
        assert params["transaction_type"] == "return_out"
        assert params["document_type"] == "purchase_return"
        assert params["quantity"] == 5.0

    def test_build_inv_return_params_uuids_converted_to_str(self) -> None:
        params = PurToInvFinancialMapper.build_inv_return_params(
            uuid4(), uuid4(), uuid4(), 1, uuid4(), uuid4(),
        )
        for key in ("tenant_id", "sku_id", "warehouse_id", "document_id", "operated_by"):
            assert isinstance(params[key], str)


class PurReconcileServiceTest:
    """PurReconcileService 采购↔WMS↔INV 三边对账测试。"""

    def test_reconcile_consistent_returns_true(self) -> None:
        result = PurReconcileService.reconcile(100.0, 100.0, 100.0)
        assert result["consistent"] is True
        assert result["pur_wms_diff"] == 0.0
        assert result["pur_inv_diff"] == 0.0
        assert result["wms_inv_diff"] == 0.0

    def test_reconcile_within_float_tolerance_consistent(self) -> None:
        # 0.001 差异经 round(...,2) 后为 0.0，视为一致
        result = PurReconcileService.reconcile(100.0, 100.004, 100.0)
        assert result["consistent"] is True

    def test_reconcile_pur_wms_mismatch_raises(self) -> None:
        with pytest.raises(PURError) as exc:
            PurReconcileService.reconcile(100.0, 90.0, 100.0)
        assert exc.value.code == PURErrorCode.WMS_INV_INCONSISTENT

    def test_reconcile_pur_inv_mismatch_raises(self) -> None:
        with pytest.raises(PURError) as exc:
            PurReconcileService.reconcile(100.0, 100.0, 80.0)
        assert exc.value.code == PURErrorCode.WMS_INV_INCONSISTENT

    def test_reconcile_wms_inv_mismatch_raises(self) -> None:
        with pytest.raises(PURError) as exc:
            PurReconcileService.reconcile(100.0, 95.0, 90.0)
        assert exc.value.code == PURErrorCode.WMS_INV_INCONSISTENT

    def test_reconcile_error_message_contains_quantities(self) -> None:
        with pytest.raises(PURError) as exc:
            PurReconcileService.reconcile(100.0, 90.0, 80.0)
        msg = exc.value.message
        assert "PUR=100.0" in msg
        assert "WMS=90.0" in msg
        assert "INV=80.0" in msg

    def test_reconcile_diffs_rounded_to_two_decimals(self) -> None:
        # 一致场景下返回的 diff 字段应被 round 到 2 位
        result = PurReconcileService.reconcile(100.0, 100.0, 100.0)
        assert result["pur_wms_diff"] == round(100.0 - 100.0, 2)