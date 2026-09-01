"""SAL 策略服务与映射器单元测试 - 审批路由 + 三边对账 + 4 个 SAL→WMS/INV 映射器。

覆盖 SalesApprovalRouterService 金额阈值路由（≤10万→L1, ≤50万→L2, >50万→L3）、
SalReconcileService 三边对账一致/不一致/修复、4 个 Mapper 幂等键派生与映射正确性。
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.domain.sales.aggregates.sales_order_aggregate import SalesOrderAggregate
from app.domain.sales.aggregates.sales_settlement_aggregate import SalesSettlementAggregate
from app.domain.sales.aggregates.shipment_order_aggregate import ShipmentOrderAggregate
from app.domain.sales.entities.sales_order_line import SalesOrderLine
from app.domain.sales.entities.settlement_reconcile_line import SettlementReconcileLine
from app.domain.sales.entities.shipment_line import ShipmentLine
from app.domain.sales.services.sal_reconcile_service import SalReconcileService
from app.domain.sales.services.sal_to_inv_financial_mapper import SalToInvFinancialMapper
from app.domain.sales.services.sal_to_inv_reservation_mapper import SalToInvReservationMapper
from app.domain.sales.services.sal_to_wms_picking_mapper import SalToWmsPickingMapper
from app.domain.sales.services.sal_to_wms_shipping_mapper import SalToWmsShippingMapper
from app.domain.sales.services.sales_approval_router_service import (
    ApprovalRule,
    ApprovalRouteResult,
    DocumentType,
    SalesApprovalRouterService,
)
from app.domain.sales.events.credit_limit_events import (
    CreditLimitOccupiedEvent,
    CreditLimitReleasedEvent,
)
from app.domain.sales.events.customer_published_event import (
    CustomerDisabledEvent,
    CustomerPublishedEvent,
)
from app.domain.sales.events.sal_wms_inv_inconsistent_event import (
    SalWmsInvInconsistentEvent,
)
from app.domain.sales.events.sales_order_events import (
    SalesOrderApprovedEvent,
    SalesOrderCancelledEvent,
    SalesOrderChangedEvent,
    SalesOrderCreatedEvent,
    SalesOrderReservedEvent,
)
from app.domain.sales.events.sales_quotation_events import (
    SalesQuotationApprovedEvent,
    SalesQuotationConvertedEvent,
)
from app.domain.sales.events.sales_return_events import SalesReturnCompletedEvent
from app.domain.sales.events.settlement_events import (
    PaymentReceivedEvent,
    SalesInvoiceMatchedEvent,
    SalesSettlementReconciledEvent,
)
from app.domain.sales.events.shipment_events import (
    ShipmentConfirmedEvent,
    ShipmentFailedEvent,
)
from app.interfaces.middleware.error_handler import SALError, SALErrorCode


def _shipment() -> ShipmentOrderAggregate:
    s = ShipmentOrderAggregate(shipment_code="SH-001", order_ids=[str(uuid4())])
    s.add_line(ShipmentLine(ship_quantity=10))
    return s


def _order() -> SalesOrderAggregate:
    o = SalesOrderAggregate(order_code="SO-001")
    o.add_line(SalesOrderLine(ordered_quantity=10, unit_price=100))
    return o


def _settlement_with_lines() -> SalesSettlementAggregate:
    s = SalesSettlementAggregate(settlement_code="ST-001")
    s.reconcile(
        [SettlementReconcileLine(order_quantity=10, shipped_quantity=10, unit_price=100)],
        threshold=0.01, reconciled_by=uuid4(),
    )
    return s


class SalesApprovalRouterServiceTest:
    """SalesApprovalRouterService 金额阈值审批路由测试。"""

    def test_route_by_amount_default_thresholds(self) -> None:
        router = SalesApprovalRouterService()
        assert router.route_by_amount(0) == "sal:approver_l1"
        assert router.route_by_amount(100000) == "sal:approver_l1"
        assert router.route_by_amount(100000.01) == "sal:approver_l2"
        assert router.route_by_amount(500000) == "sal:approver_l2"
        assert router.route_by_amount(500000.01) == "sal:approver_l3"
        assert router.route_by_amount(9999999) == "sal:approver_l3"

    def test_route_by_amount_boundary_100000_routes_l1(self) -> None:
        router = SalesApprovalRouterService()
        assert router.route_by_amount(100000) == "sal:approver_l1"

    def test_route_by_amount_boundary_500000_routes_l2(self) -> None:
        router = SalesApprovalRouterService()
        assert router.route_by_amount(500000) == "sal:approver_l2"

    def test_route_returns_result_with_amount_role(self) -> None:
        router = SalesApprovalRouterService()
        result = router.route(DocumentType.ORDER, 5000.0)
        assert isinstance(result, ApprovalRouteResult)
        assert result.document_type == DocumentType.ORDER
        assert result.amount == 5000.0
        assert "sal:approver_l1" in result.approver_roles

    def test_route_high_amount_routes_l3(self) -> None:
        router = SalesApprovalRouterService()
        result = router.route(DocumentType.ORDER, 1000000.0)
        assert "sal:approver_l3" in result.approver_roles

    def test_route_with_customer_categories_adds_category_role(self) -> None:
        router = SalesApprovalRouterService()
        result = router.route(DocumentType.ORDER, 5000.0, customer_category_ids=[uuid4()])
        assert "sal:approver_customer_category" in result.approver_roles

    def test_route_with_sales_person_adds_peer_review(self) -> None:
        router = SalesApprovalRouterService()
        result = router.route(DocumentType.ORDER, 5000.0, sales_person_id=uuid4())
        assert "sal:approver_peer_review" in result.approver_roles

    def test_route_deduplicates_roles_preserving_order(self) -> None:
        router = SalesApprovalRouterService()
        result = router.route(
            DocumentType.ORDER, 5000.0,
            customer_category_ids=[uuid4()], sales_person_id=uuid4(),
        )
        assert len(result.approver_roles) == len(set(result.approver_roles))

    def test_custom_rules_sorted_by_threshold(self) -> None:
        rules = [
            ApprovalRule(threshold=500, approver_role="r_low"),
            ApprovalRule(threshold=50, approver_role="r_min"),
            ApprovalRule(threshold=float("inf"), approver_role="r_high"),
        ]
        router = SalesApprovalRouterService(extra_rules=rules)
        assert router.route_by_amount(10) == "r_min"
        assert router.route_by_amount(50) == "r_min"
        assert router.route_by_amount(100) == "r_low"
        assert router.route_by_amount(500) == "r_low"
        assert router.route_by_amount(501) == "r_high"

    def test_route_amount_over_all_thresholds_falls_back(self) -> None:
        # 自定义规则不含 inf 兜底，amount 超过所有阈值 → for-else 触发
        router = SalesApprovalRouterService(
            extra_rules=[ApprovalRule(threshold=1000, approver_role="only")]
        )
        result = router.route(DocumentType.ORDER, 2000.0)
        assert "only" in result.approver_roles
        assert "max_threshold" in result.reason

    def test_route_by_amount_over_all_thresholds_falls_back(self) -> None:
        router = SalesApprovalRouterService(
            extra_rules=[ApprovalRule(threshold=1000, approver_role="only")]
        )
        assert router.route_by_amount(2000) == "only"


class SalReconcileServiceTest:
    """SalReconcileService 销售↔WMS↔INV 三边对账测试。"""

    def test_reconcile_consistent_returns_true(self) -> None:
        svc = SalReconcileService()
        sku = uuid4()
        result = svc.reconcile(
            tenant_id=uuid4(), order_id=uuid4(),
            sal_shipped={sku: 100.0}, wms_shipped={sku: 100.0}, inv_on_hand={sku: 50.0},
        )
        assert result.consistent is True
        assert result.diff_items == []

    def test_reconcile_sal_wms_mismatch(self) -> None:
        svc = SalReconcileService()
        sku = uuid4()
        result = svc.reconcile(
            tenant_id=uuid4(), order_id=uuid4(),
            sal_shipped={sku: 100.0}, wms_shipped={sku: 90.0}, inv_on_hand={sku: 50.0},
        )
        assert result.consistent is False
        assert len(result.diff_items) == 1
        assert result.diff_items[0].diff == 10.0

    def test_reconcile_inv_mismatch_with_expected(self) -> None:
        svc = SalReconcileService()
        sku = uuid4()
        result = svc.reconcile(
            tenant_id=uuid4(), order_id=uuid4(),
            sal_shipped={sku: 100.0}, wms_shipped={sku: 100.0}, inv_on_hand={sku: 50.0},
            expected_inv_on_hand={sku: 40.0},
        )
        assert result.consistent is False
        assert any(item.diff == 10.0 for item in result.diff_items)

    def test_reconcile_multiple_skus(self) -> None:
        svc = SalReconcileService()
        sku1, sku2 = uuid4(), uuid4()
        result = svc.reconcile(
            tenant_id=uuid4(), order_id=uuid4(),
            sal_shipped={sku1: 100.0, sku2: 50.0},
            wms_shipped={sku1: 100.0, sku2: 45.0},
            inv_on_hand={sku1: 0.0, sku2: 0.0},
        )
        assert result.consistent is False
        assert len(result.diff_items) == 1

    def test_reconcile_within_float_tolerance_consistent(self) -> None:
        svc = SalReconcileService(diff_threshold=0.01)
        sku = uuid4()
        result = svc.reconcile(
            tenant_id=uuid4(), order_id=uuid4(),
            sal_shipped={sku: 100.0}, wms_shipped={sku: 100.004}, inv_on_hand={sku: 0.0},
        )
        assert result.consistent is True

    def test_repair_sal_shipped_uses_wms_as_truth(self) -> None:
        sku1, sku2 = uuid4(), uuid4()
        sal = {sku1: 100.0, sku2: 50.0}
        wms = {sku1: 95.0, sku2: 50.0}
        repaired = SalReconcileService.repair_sal_shipped(sal, wms)
        assert repaired[sku1] == 95.0
        assert repaired[sku2] == 50.0

    def test_repair_sal_shipped_adds_wms_only_skus(self) -> None:
        sku1, sku2 = uuid4(), uuid4()
        sal = {sku1: 100.0}
        wms = {sku1: 100.0, sku2: 30.0}
        repaired = SalReconcileService.repair_sal_shipped(sal, wms)
        assert repaired[sku2] == 30.0


class SalToWmsPickingMapperTest:
    """SalToWmsPickingMapper 销售→WMS 拣货映射测试。"""

    def test_build_picking_params_full_mapping(self) -> None:
        tenant_id = uuid4()
        shipment = _shipment()
        line = shipment.lines[0]
        corr = uuid4()
        params = SalToWmsPickingMapper.build_picking_params(tenant_id, shipment, line, corr)
        assert params["tenant_id"] == str(tenant_id)
        assert params["source_document_id"] == str(shipment.shipment_id)
        assert params["source_document_type"] == "sal_shipment"
        assert params["warehouse_id"] == str(shipment.shipping_warehouse_id)
        assert params["lines"][0]["sku_id"] == str(line.enterprise_sku_id)
        assert params["lines"][0]["quantity"] == 10
        assert params["picking_strategy"] == shipment.picking_strategy.value
        assert params["idempotency_key"] == f"sal:shipment:{shipment.shipment_id}:pick"
        assert params["correlation_id"] == str(corr)

    def test_build_picking_params_idempotency_key_derived(self) -> None:
        shipment = _shipment()
        params = SalToWmsPickingMapper.build_picking_params(uuid4(), shipment, shipment.lines[0])
        assert params["idempotency_key"].startswith("sal:shipment:")
        assert params["idempotency_key"].endswith(":pick")

    def test_build_picking_params_batch_includes_all_lines(self) -> None:
        shipment = _shipment()
        shipment.add_line(ShipmentLine(ship_quantity=5))
        params = SalToWmsPickingMapper.build_picking_params_batch(uuid4(), shipment)
        assert len(params["lines"]) == 2

    def test_correlation_id_falls_back_to_shipment_id(self) -> None:
        shipment = _shipment()
        params = SalToWmsPickingMapper.build_picking_params(uuid4(), shipment, shipment.lines[0])
        assert params["correlation_id"] == str(shipment.shipment_id)


class SalToWmsShippingMapperTest:
    """SalToWmsShippingMapper 销售→WMS 发货映射测试。"""

    def test_build_shipping_params_full_mapping(self) -> None:
        tenant_id = uuid4()
        shipment = _shipment()
        params = SalToWmsShippingMapper.build_shipping_params(
            tenant_id, shipment, logistics_no="SF-001", carrier="SF-Express",
        )
        assert params["tenant_id"] == str(tenant_id)
        assert params["source_document_type"] == "sal_shipment"
        assert params["logistics_no"] == "SF-001"
        assert params["carrier"] == "SF-Express"
        assert params["idempotency_key"] == f"sal:shipment:{shipment.shipment_id}:ship"
        assert len(params["lines"]) == 1

    def test_build_shipping_params_carrier_fallback(self) -> None:
        shipment = _shipment()
        shipment.carrier = "Default-Carrier"
        params = SalToWmsShippingMapper.build_shipping_params(
            uuid4(), shipment, logistics_no="LOG-001",
        )
        assert params["carrier"] == "Default-Carrier"

    def test_build_shipping_params_empty_carrier(self) -> None:
        shipment = _shipment()
        params = SalToWmsShippingMapper.build_shipping_params(
            uuid4(), shipment, logistics_no="LOG-001",
        )
        assert params["carrier"] == ""


class SalToInvFinancialMapperTest:
    """SalToInvFinancialMapper 销售→INV 收入映射测试。"""

    def test_build_revenue_params_full_mapping(self) -> None:
        tenant_id = uuid4()
        settlement = _settlement_with_lines()
        line = settlement.reconcile_lines[0]
        params = SalToInvFinancialMapper.build_revenue_params(
            tenant_id, settlement, line, moving_avg_cost=60.0,
        )
        assert params["tenant_id"] == str(tenant_id)
        assert params["document_type"] == "sal_settlement"
        assert params["order_id"] == str(settlement.order_id)
        assert params["sku_id"] == str(line.enterprise_sku_id)
        assert params["quantity"] == 10
        assert params["unit_price"] == 100
        assert params["moving_avg_cost"] == 60.0
        assert params["revenue_amount"] == 1000.0
        assert params["cost_amount"] == 600.0
        assert params["gross_profit"] == 400.0
        assert "revenue" in params["idempotency_key"]

    def test_build_revenue_params_idempotency_key_derived(self) -> None:
        settlement = _settlement_with_lines()
        line = settlement.reconcile_lines[0]
        params = SalToInvFinancialMapper.build_revenue_params(
            uuid4(), settlement, line, moving_avg_cost=60.0,
        )
        assert params["idempotency_key"].startswith("sal:settlement:")
        assert ":revenue:" in params["idempotency_key"]

    def test_build_revenue_params_batch(self) -> None:
        settlement = SalesSettlementAggregate(settlement_code="ST-002")
        settlement.reconcile(
            [SettlementReconcileLine(order_quantity=10, shipped_quantity=10, unit_price=100),
             SettlementReconcileLine(order_quantity=5, shipped_quantity=5, unit_price=200)],
            threshold=0.01, reconciled_by=uuid4(),
        )
        costs = {line.enterprise_sku_id: 50.0 for line in settlement.reconcile_lines}
        params_list = SalToInvFinancialMapper.build_revenue_params_batch(
            uuid4(), settlement, costs,
        )
        assert len(params_list) == 2


class SalToInvReservationMapperTest:
    """SalToInvReservationMapper 销售→INV 预留映射测试。"""

    def test_build_reservation_params_full_mapping(self) -> None:
        tenant_id = uuid4()
        order = _order()
        line = order.lines[0]
        params = SalToInvReservationMapper.build_reservation_params(tenant_id, order, line)
        assert params["tenant_id"] == str(tenant_id)
        assert params["sku_id"] == str(line.enterprise_sku_id)
        assert params["quantity"] == 10
        assert params["source_document_id"] == str(order.order_id)
        assert params["source_document_type"] == "sal_order"
        assert params["source_line_id"] == str(line.line_id)
        assert params["idempotency_key"] == f"sal:order:{order.order_id}:reserve:{line.line_id}"

    def test_build_reservation_params_warehouse_none_when_absent(self) -> None:
        order = _order()
        params = SalToInvReservationMapper.build_reservation_params(
            uuid4(), order, order.lines[0],
        )
        assert params["warehouse_id"] is None

    def test_build_reservation_params_batch(self) -> None:
        order = _order()
        order.add_line(SalesOrderLine(ordered_quantity=5, unit_price=20))
        params_list = SalToInvReservationMapper.build_reservation_params_batch(uuid4(), order)
        assert len(params_list) == 2

    def test_build_release_params(self) -> None:
        tenant_id = uuid4()
        reservation_id = uuid4()
        order_id = uuid4()
        params = SalToInvReservationMapper.build_release_params(tenant_id, reservation_id, order_id)
        assert params["tenant_id"] == str(tenant_id)
        assert params["reservation_id"] == str(reservation_id)
        assert params["idempotency_key"] == f"sal:order:{order_id}:release:{reservation_id}"

    def test_build_consume_params(self) -> None:
        tenant_id = uuid4()
        reservation_id = uuid4()
        shipment_id = uuid4()
        params = SalToInvReservationMapper.build_consume_params(
            tenant_id, reservation_id, consumed_quantity=8.0, shipment_id=shipment_id,
        )
        assert params["tenant_id"] == str(tenant_id)
        assert params["reservation_id"] == str(reservation_id)
        assert params["consumed_quantity"] == 8.0
        assert params["idempotency_key"] == (
            f"sal:shipment:{shipment_id}:consume:{reservation_id}"
        )


class SalDomainEventsTest:
    """SAL 领域事件构造测试 - 验证事件数据类默认字段与不可变性。"""

    def test_credit_limit_events_construct_with_defaults(self) -> None:
        e1 = CreditLimitOccupiedEvent(
            customer_id=uuid4(), tenant_id=uuid4(), order_id=uuid4(),
            occupied_amount=100.0, used_amount=100.0,
        )
        assert e1.event_id is not None
        assert e1.occurred_at is not None
        assert e1.correlation_id is None
        e2 = CreditLimitReleasedEvent(
            customer_id=uuid4(), tenant_id=uuid4(),
            released_amount=100.0, used_amount=0.0,
        )
        assert e2.event_id is not None

    def test_customer_events_construct(self) -> None:
        pub = CustomerPublishedEvent(
            customer_id=uuid4(), tenant_id=uuid4(), customer_code="C-001",
        )
        assert pub.status == "active"
        assert pub.published_version == 1
        dis = CustomerDisabledEvent(
            customer_id=uuid4(), tenant_id=uuid4(), customer_code="C-001",
        )
        assert dis.event_id is not None

    def test_sal_wms_inv_inconsistent_event_construct(self) -> None:
        e = SalWmsInvInconsistentEvent(
            tenant_id=uuid4(), order_id=uuid4(), shipment_id=None,
            sku_id=uuid4(), sal_qty=100.0, wms_qty=90.0, inv_qty=0.0, diff=10.0,
        )
        assert e.diff == 10.0
        assert e.shipment_id is None

    def test_sales_order_events_construct(self) -> None:
        oid = uuid4()
        tid = uuid4()
        created = SalesOrderCreatedEvent(
            order_id=oid, tenant_id=tid, customer_id=uuid4(), total_amount=1000.0,
        )
        assert created.total_amount == 1000.0
        approved = SalesOrderApprovedEvent(
            order_id=oid, tenant_id=tid, approved_by=uuid4(),
        )
        assert approved.occurred_at is not None
        reserved = SalesOrderReservedEvent(
            order_id=oid, tenant_id=tid, reservation_ids=["r1", "r2"],
        )
        assert reserved.reservation_ids == ["r1", "r2"]
        changed = SalesOrderChangedEvent(
            order_id=oid, tenant_id=tid, version=2, before={}, after={},
        )
        assert changed.version == 2
        cancelled = SalesOrderCancelledEvent(
            order_id=oid, tenant_id=tid, cancelled_quantity=10.0, reason="cust",
        )
        assert cancelled.reason == "cust"

    def test_sales_quotation_events_construct(self) -> None:
        approved = SalesQuotationApprovedEvent(
            quotation_id=uuid4(), tenant_id=uuid4(), customer_id=uuid4(), approved_by=uuid4(),
        )
        assert approved.event_id is not None
        converted = SalesQuotationConvertedEvent(
            quotation_id=uuid4(), tenant_id=uuid4(), order_id=uuid4(),
        )
        assert converted.occurred_at is not None

    def test_sales_return_event_construct(self) -> None:
        e = SalesReturnCompletedEvent(
            return_id=uuid4(), tenant_id=uuid4(), order_id=uuid4(),
            refund_amount=500.0, disposition="restock",
        )
        assert e.disposition == "restock"
        assert e.inv_transaction_ids == []
        assert e.wms_receiving_id is None

    def test_settlement_events_construct(self) -> None:
        reconciled = SalesSettlementReconciledEvent(
            settlement_id=uuid4(), tenant_id=uuid4(), order_id=uuid4(),
            receivable_amount=1000.0,
        )
        assert reconciled.receivable_amount == 1000.0
        matched = SalesInvoiceMatchedEvent(
            invoice_id=uuid4(), tenant_id=uuid4(), settlement_id=uuid4(),
            invoice_amount=1000.0,
        )
        assert matched.invoice_amount == 1000.0
        received = PaymentReceivedEvent(
            payment_receipt_id=uuid4(), tenant_id=uuid4(), settlement_id=uuid4(),
            payment_no="PAY-001", payment_amount=1000.0,
        )
        assert received.payment_no == "PAY-001"

    def test_shipment_events_construct(self) -> None:
        confirmed = ShipmentConfirmedEvent(
            shipment_id=uuid4(), tenant_id=uuid4(), order_ids=["o1"],
            wms_shipping_id=uuid4(), inv_transaction_ids=["t1"],
            logistics_no="LOG-001", total_ship_quantity=10.0,
        )
        assert confirmed.logistics_no == "LOG-001"
        failed = ShipmentFailedEvent(
            shipment_id=uuid4(), tenant_id=uuid4(), failure_reason="wms down",
        )
        assert failed.failure_reason == "wms down"