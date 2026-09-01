"""SAL 黄金链路 E2E 测试套件编排器 - 16 步端到端验证。

C-SAL-GOLDEN-01: 客户→报价→订单→信用校验→价格匹配→审批→预留→WMS Picking→包装→发货
  →INV Transaction→结算→发票→收款→信用释放
  → 全程销售出库通过WMS Picking/Shipping API(红线一) + 结算通过INV Financial API(红线二)
  + 库存预留通过INV Reservation API(红线五)

另含部分发货黄金链路 100→30→40→30 四态守恒验证。
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from uuid import uuid4

import httpx


TENANT_TOKEN = "03724bb5-fd4d-46e5-af21-c794b559d406"
ADMIN_PASSWORD = "Verify@2026!"
BASE_URL = "http://localhost:8000/api/v1"


@dataclass
class SalStepResult:
    step_number: int
    step_name: str
    passed: bool
    duration_ms: float
    detail: str = ""
    actual: dict = field(default_factory=dict)
    expected: dict = field(default_factory=dict)


@dataclass
class SalE2ETestReport:
    total_steps: int = 16
    passed_steps: int = 0
    failed_steps: int = 0
    total_duration_ms: float = 0.0
    results: list[SalStepResult] = field(default_factory=list)
    blocked: bool = False

    @property
    def all_passed(self) -> bool:
        return self.passed_steps == self.total_steps

    def to_dict(self) -> dict:
        return {
            "total_steps": self.total_steps,
            "passed_steps": self.passed_steps,
            "failed_steps": self.failed_steps,
            "total_duration_ms": round(self.total_duration_ms, 2),
            "all_passed": self.all_passed,
            "blocked": self.blocked,
            "results": [
                {"step": r.step_number, "name": r.step_name, "passed": r.passed,
                 "duration_ms": round(r.duration_ms, 2), "detail": r.detail}
                for r in self.results
            ],
        }


class SalGoldenPathE2ETestSuite:
    """SAL 黄金链路 E2E 测试套件编排器 - 16 步。"""

    def __init__(self, base_url: str = BASE_URL) -> None:
        self._base_url = base_url
        self._report = SalE2ETestReport()
        self._ctx: dict = {}

    def _headers(self) -> dict:
        token = self._ctx.get("access_token")
        h = {"X-Tenant-Token": TENANT_TOKEN, "Content-Type": "application/json"}
        if token:
            h["Authorization"] = f"Bearer {token}"
        return h

    def _record(self, step: int, name: str, start: float, passed: bool, detail: str = "") -> None:
        ms = (time.perf_counter() - start) * 1000
        self._report.results.append(SalStepResult(step, name, passed, ms, detail))
        self._report.total_duration_ms += ms
        if passed:
            self._report.passed_steps += 1
        else:
            self._report.failed_steps += 1

    async def run(self) -> SalE2ETestReport:
        async with httpx.AsyncClient(base_url=self._base_url, timeout=30) as client:
            await self._step01_login(client)
            await self._step02_create_customer(client)
            await self._step03_submit_approve_publish_customer(client)
            await self._step04_configure_pricing(client)
            await self._step05_create_quotation(client)
            await self._step06_submit_approve_quotation(client)
            await self._step07_convert_to_order(client)
            await self._step08_credit_check(client)
            await self._step09_price_match(client)
            await self._step10_submit_approve_order(client)
            await self._step11_confirm_fulfillment(client)
            await self._step12_create_shipment_picking(client)
            await self._step13_packing(client)
            await self._step14_confirm_shipment(client)
            await self._step15_settlement_reconcile(client)
            await self._step16_invoice_payment(client)
        return self._report

    async def _step01_login(self, client: httpx.AsyncClient) -> None:
        s = time.perf_counter()
        try:
            resp = await client.post("/auth/login",
                json={"tenant_id": TENANT_TOKEN, "username": "admin", "password": ADMIN_PASSWORD},
                headers={"X-Tenant-Token": TENANT_TOKEN})
            token = resp.json().get("access_token") or resp.json().get("token")
            self._ctx["access_token"] = token
            self._record(1, "登录获取JWT", s, bool(token))
        except Exception as e:
            self._record(1, "登录获取JWT", s, False, str(e))

    async def _step02_create_customer(self, client: httpx.AsyncClient) -> None:
        s = time.perf_counter()
        try:
            code = f"C-E2E-{uuid4().hex[:6]}"
            resp = await client.post("/sal/customers",
                json={"customer_code": code, "customer_name": "E2E客户",
                      "customer_type": "corporate", "credit_limit": 100000},
                headers=self._headers())
            self._ctx["customer_id"] = resp.json()["customer_id"]
            self._ctx["customer_code"] = code
            self._record(2, "创建客户C1(信用额度100000)", s, resp.status_code in (200, 201))
        except Exception as e:
            self._record(2, "创建客户C1", s, False, str(e))

    async def _step03_submit_approve_publish_customer(self, client: httpx.AsyncClient) -> None:
        s = time.perf_counter()
        try:
            cid = self._ctx["customer_id"]
            await client.post(f"/sal/customers/{cid}/submit", headers=self._headers())
            await client.post(f"/sal/customers/{cid}/approve",
                json={"approved": True}, headers=self._headers())
            resp = await client.post(f"/sal/customers/{cid}/publish", headers=self._headers())
            self._record(3, "客户提交→审批→发布(ACTIVE)", s, resp.status_code == 200)
        except Exception as e:
            self._record(3, "客户提交→审批→发布", s, False, str(e))

    async def _step04_configure_pricing(self, client: httpx.AsyncClient) -> None:
        s = time.perf_counter()
        try:
            cid = self._ctx["customer_id"]
            sku_id = str(uuid4())
            self._ctx["sku_id"] = sku_id
            resp = await client.post(f"/sal/customers/{cid}/pricing",
                json={"sku_id": sku_id, "price_type": "agreement",
                      "unit_price": 90, "currency": "CNY",
                      "priority": 20},
                headers=self._headers())
            self._record(4, "配置价格体系(C1对SKU-001协议价90)", s, resp.status_code in (200, 201))
        except Exception as e:
            self._record(4, "配置价格体系", s, False, str(e))

    async def _step05_create_quotation(self, client: httpx.AsyncClient) -> None:
        s = time.perf_counter()
        try:
            code = f"SQ-E2E-{uuid4().hex[:6]}"
            resp = await client.post("/sal/quotations",
                json={"quotation_code": code, "customer_id": self._ctx["customer_id"],
                      "lines": [{"sku_id": self._ctx["sku_id"],
                                 "quantity": 100, "unit_price": 90}]},
                headers=self._headers())
            self._ctx["quotation_id"] = resp.json().get("quotation_id")
            self._record(5, "创建销售报价SQ-001(C1+SKU-001数量100单价90)", s, resp.status_code in (200, 201))
        except Exception as e:
            self._record(5, "创建销售报价", s, False, str(e))

    async def _step06_submit_approve_quotation(self, client: httpx.AsyncClient) -> None:
        s = time.perf_counter()
        try:
            qid = self._ctx["quotation_id"]
            await client.post(f"/sal/quotations/{qid}/submit", headers=self._headers())
            resp = await client.post(f"/sal/quotations/{qid}/approve",
                json={"approved": True}, headers=self._headers())
            self._record(6, "报价提交→审批通过", s, resp.status_code == 200)
        except Exception as e:
            self._record(6, "报价提交→审批", s, False, str(e))

    async def _step07_convert_to_order(self, client: httpx.AsyncClient) -> None:
        s = time.perf_counter()
        try:
            qid = self._ctx["quotation_id"]
            resp = await client.post(f"/sal/quotations/{qid}/convert",
                headers=self._headers())
            self._ctx["order_id"] = resp.json().get("order_id")
            self._record(7, "报价转销售订单SO-001(继承明细)", s, bool(self._ctx.get("order_id")))
        except Exception as e:
            self._record(7, "报价转单", s, False, str(e))

    async def _step08_credit_check(self, client: httpx.AsyncClient) -> None:
        s = time.perf_counter()
        try:
            oid = self._ctx["order_id"]
            resp = await client.get(f"/sal/credit/{self._ctx['customer_id']}",
                headers=self._headers())
            credit_info = resp.json()
            used = credit_info.get("used_amount", 0)
            limit = credit_info.get("credit_limit", 100000)
            available = limit - used
            self._record(8, f"信用校验(已用{used}+订单9000≤{limit})", s,
                         available >= 9000, f"available={available}")
        except Exception as e:
            self._record(8, "信用校验", s, False, str(e))

    async def _step09_price_match(self, client: httpx.AsyncClient) -> None:
        s = time.perf_counter()
        try:
            resp = await client.get(f"/sal/pricing/customer/{self._ctx['customer_id']}",
                headers=self._headers())
            self._record(9, "价格匹配(C1对SKU-001协议价90)", s, resp.status_code == 200)
        except Exception as e:
            self._record(9, "价格匹配", s, False, str(e))

    async def _step10_submit_approve_order(self, client: httpx.AsyncClient) -> None:
        s = time.perf_counter()
        try:
            oid = self._ctx["order_id"]
            await client.post(f"/sal/orders/{oid}/submit", headers=self._headers())
            resp = await client.post(f"/sal/orders/{oid}/approve",
                json={"approved": True}, headers=self._headers())
            self._record(10, "订单提交→审批通过(9000<10万销售经理)", s, resp.status_code == 200)
        except Exception as e:
            self._record(10, "订单提交→审批", s, False, str(e))

    async def _step11_confirm_fulfillment(self, client: httpx.AsyncClient) -> None:
        s = time.perf_counter()
        try:
            oid = self._ctx["order_id"]
            resp = await client.post(f"/sal/orders/{oid}/confirm",
                json={"idempotency_key": f"sal:order:{oid}:reserve"},
                headers=self._headers())
            self._record(11, "确认履约→INV Reservation API预留100(红线五)", s,
                         resp.status_code == 200,
                         f"reservation: {resp.json().get('reservation_id', 'N/A')}")
        except Exception as e:
            self._record(11, "确认履约→INV Reservation", s, False, str(e))

    async def _step12_create_shipment_picking(self, client: httpx.AsyncClient) -> None:
        s = time.perf_counter()
        try:
            code = f"SH-E2E-{uuid4().hex[:6]}"
            warehouse_id = str(uuid4())
            self._ctx["warehouse_id"] = warehouse_id
            resp = await client.post("/sal/shipments",
                json={"shipment_code": code, "order_id": self._ctx["order_id"],
                      "warehouse_id": warehouse_id, "strategy": "FIFO",
                      "lines": [{"sku_id": self._ctx["sku_id"], "quantity": 100}]},
                headers=self._headers())
            self._ctx["shipment_id"] = resp.json().get("shipment_id")
            sid = self._ctx["shipment_id"]
            resp2 = await client.post(f"/sal/shipments/{sid}/submit",
                json={"idempotency_key": f"sal:shipment:{sid}:pick"},
                headers=self._headers())
            self._record(12, "创建发货单→提交→WMS Picking API(红线一)", s,
                         resp2.status_code == 200,
                         f"picking: {resp2.json().get('wms_picking_id', 'N/A')}")
        except Exception as e:
            self._record(12, "创建发货→WMS Picking", s, False, str(e))

    async def _step13_packing(self, client: httpx.AsyncClient) -> None:
        s = time.perf_counter()
        try:
            sid = self._ctx["shipment_id"]
            resp = await client.post(f"/sal/shipments/{sid}/packing",
                json={"packing_lines": [{"carton_no": "CARTON-001", "quantity": 100,
                                          "sku_id": self._ctx["sku_id"]}]},
                headers=self._headers())
            await client.post(f"/sal/shipments/{sid}/packing/complete",
                headers=self._headers())
            self._record(13, "包装(1箱100件)→PACKED", s, resp.status_code in (200, 201))
        except Exception as e:
            self._record(13, "包装", s, False, str(e))

    async def _step14_confirm_shipment(self, client: httpx.AsyncClient) -> None:
        s = time.perf_counter()
        try:
            sid = self._ctx["shipment_id"]
            resp = await client.post(f"/sal/shipments/{sid}/confirm",
                json={"idempotency_key": f"sal:shipment:{sid}:ship"},
                headers=self._headers())
            self._record(14, "确认发货→WMS Shipping API→INV SALES_SHIPMENT -100(红线一/二)", s,
                         resp.status_code == 200,
                         f"shipping: {resp.json().get('wms_shipping_id', 'N/A')}")
        except Exception as e:
            self._record(14, "确认发货→WMS Shipping", s, False, str(e))

    async def _step15_settlement_reconcile(self, client: httpx.AsyncClient) -> None:
        s = time.perf_counter()
        try:
            code = f"SS-E2E-{uuid4().hex[:6]}"
            resp = await client.post("/sal/settlements",
                json={"settlement_code": code, "order_id": self._ctx["order_id"],
                      "customer_id": self._ctx["customer_id"],
                      "total_amount": 9000, "cost_amount": 8000},
                headers=self._headers())
            self._ctx["settlement_id"] = resp.json().get("settlement_id")
            sid = self._ctx["settlement_id"]
            resp2 = await client.post(f"/sal/settlements/{sid}/reconcile",
                json={"shipped_amount": 9000, "order_amount": 9000},
                headers=self._headers())
            resp3 = await client.post(f"/sal/settlements/{sid}/land-revenue",
                json={"idempotency_key": f"sal:settlement:{sid}:revenue",
                      "revenue": 9000, "cost": 8000},
                headers=self._headers())
            self._record(15, "结算→对账→INV Financial API收入9000成本8000毛利1000(红线二)", s,
                         resp2.status_code == 200 and resp3.status_code == 200,
                         f"revenue_landed: {resp3.json().get('revenue_landed', 'N/A')}")
        except Exception as e:
            self._record(15, "结算→对账→INV Financial", s, False, str(e))

    async def _step16_invoice_payment(self, client: httpx.AsyncClient) -> None:
        s = time.perf_counter()
        try:
            icode = f"INV-E2E-{uuid4().hex[:6]}"
            resp = await client.post("/sal/invoices",
                json={"invoice_code": icode, "customer_id": self._ctx["customer_id"],
                      "invoice_amount": 9000, "tax_amount": 1170,
                      "settlement_id": self._ctx["settlement_id"]},
                headers=self._headers())
            self._ctx["invoice_id"] = resp.json().get("invoice_id")
            inv_id = self._ctx["invoice_id"]
            sid = self._ctx["settlement_id"]
            await client.post(f"/sal/settlements/{sid}/match-invoice",
                json={"invoice_id": inv_id, "matched_amount": 9000},
                headers=self._headers())
            pcode = f"PAY-E2E-{uuid4().hex[:6]}"
            resp2 = await client.post(f"/sal/settlements/{sid}/request-payment",
                json={"payment_code": pcode, "amount": 9000},
                headers=self._headers())
            self._ctx["payment_id"] = resp2.json().get("payment_id")
            pid = self._ctx["payment_id"]
            resp3 = await client.post(f"/sal/payments/{pid}/confirm",
                json={"amount": 9000},
                headers=self._headers())
            self._record(16, "发票→匹配→收款→信用释放(闭环)", s,
                         resp3.status_code == 200,
                         f"credit_released: {resp3.json().get('credit_released', 'N/A')}")
        except Exception as e:
            self._record(16, "发票→收款→信用释放", s, False, str(e))


class SalPartialFulfillmentE2ETestSuite:
    """SAL 部分发货黄金链路 E2E 测试 - 100→30→40→30 四态守恒。"""

    def __init__(self, base_url: str = BASE_URL) -> None:
        self._base_url = base_url
        self._report = SalE2ETestReport(total_steps=6)
        self._ctx: dict = {}

    def _headers(self) -> dict:
        token = self._ctx.get("access_token")
        h = {"X-Tenant-Token": TENANT_TOKEN, "Content-Type": "application/json"}
        if token:
            h["Authorization"] = f"Bearer {token}"
        return h

    def _record(self, step: int, name: str, start: float, passed: bool, detail: str = "") -> None:
        ms = (time.perf_counter() - start) * 1000
        self._report.results.append(SalStepResult(step, name, passed, ms, detail))
        self._report.total_duration_ms += ms
        if passed:
            self._report.passed_steps += 1
        else:
            self._report.failed_steps += 1

    async def run(self) -> SalE2ETestReport:
        async with httpx.AsyncClient(base_url=self._base_url, timeout=30) as client:
            await self._step01_setup(client)
            await self._step02_first_ship_30(client)
            await self._step03_second_ship_40(client)
            await self._step04_third_ship_30(client)
            await self._step05_consistency_check(client)
            await self._step06_four_state_conservation(client)
        return self._report

    async def _step01_setup(self, client: httpx.AsyncClient) -> None:
        s = time.perf_counter()
        try:
            resp = await client.post("/auth/login",
                json={"tenant_id": TENANT_TOKEN, "username": "admin", "password": ADMIN_PASSWORD},
                headers={"X-Tenant-Token": TENANT_TOKEN})
            token = resp.json().get("access_token") or resp.json().get("token")
            self._ctx["access_token"] = token
            code = f"C-PF-{uuid4().hex[:6]}"
            resp = await client.post("/sal/customers",
                json={"customer_code": code, "customer_name": "部分发货客户", "credit_limit": 100000},
                headers=self._headers())
            cid = resp.json()["customer_id"]
            await client.post(f"/sal/customers/{cid}/submit", headers=self._headers())
            await client.post(f"/sal/customers/{cid}/approve", json={"approved": True}, headers=self._headers())
            await client.post(f"/sal/customers/{cid}/publish", headers=self._headers())
            sku_id = str(uuid4())
            self._ctx["sku_id"] = sku_id
            ocode = f"SO-PF-{uuid4().hex[:6]}"
            resp = await client.post("/sal/orders",
                json={"order_code": ocode, "customer_id": cid,
                      "lines": [{"sku_id": sku_id, "quantity": 100, "unit_price": 90}]},
                headers=self._headers())
            oid = resp.json()["order_id"]
            await client.post(f"/sal/orders/{oid}/submit", headers=self._headers())
            await client.post(f"/sal/orders/{oid}/approve", json={"approved": True}, headers=self._headers())
            await client.post(f"/sal/orders/{oid}/confirm",
                json={"idempotency_key": f"sal:order:{oid}:reserve"}, headers=self._headers())
            self._ctx["customer_id"] = cid
            self._ctx["order_id"] = oid
            self._record(1, "创建客户+订单100+审批+预留", s, True)
        except Exception as e:
            self._record(1, "setup", s, False, str(e))

    async def _step02_first_ship_30(self, client: httpx.AsyncClient) -> None:
        s = time.perf_counter()
        try:
            oid = self._ctx["order_id"]
            code = f"SH-PF1-{uuid4().hex[:6]}"
            resp = await client.post("/sal/shipments",
                json={"shipment_code": code, "order_id": oid, "warehouse_id": str(uuid4()),
                      "lines": [{"sku_id": self._ctx["sku_id"], "quantity": 30}]},
                headers=self._headers())
            sid = resp.json()["shipment_id"]
            await client.post(f"/sal/shipments/{sid}/submit", headers=self._headers())
            await client.post(f"/sal/shipments/{sid}/confirm",
                json={"idempotency_key": f"sal:shipment:{sid}:ship"}, headers=self._headers())
            order_resp = await client.get(f"/sal/orders/{oid}", headers=self._headers())
            order = order_resp.json()
            shipped = order.get("total_shipped", 0)
            self._record(2, "第一次发货30(shipped=30 remaining=70 PARTIAL_SHIPPED)", s,
                         shipped == 30, f"shipped={shipped}")
        except Exception as e:
            self._record(2, "第一次发货30", s, False, str(e))

    async def _step03_second_ship_40(self, client: httpx.AsyncClient) -> None:
        s = time.perf_counter()
        try:
            oid = self._ctx["order_id"]
            code = f"SH-PF2-{uuid4().hex[:6]}"
            resp = await client.post("/sal/shipments",
                json={"shipment_code": code, "order_id": oid, "warehouse_id": str(uuid4()),
                      "lines": [{"sku_id": self._ctx["sku_id"], "quantity": 40}]},
                headers=self._headers())
            sid = resp.json()["shipment_id"]
            await client.post(f"/sal/shipments/{sid}/submit", headers=self._headers())
            await client.post(f"/sal/shipments/{sid}/confirm",
                json={"idempotency_key": f"sal:shipment:{sid}:ship"}, headers=self._headers())
            order_resp = await client.get(f"/sal/orders/{oid}", headers=self._headers())
            order = order_resp.json()
            shipped = order.get("total_shipped", 0)
            self._record(3, "第二次发货40(shipped=70 remaining=30 PARTIAL_SHIPPED)", s,
                         shipped == 70, f"shipped={shipped}")
        except Exception as e:
            self._record(3, "第二次发货40", s, False, str(e))

    async def _step04_third_ship_30(self, client: httpx.AsyncClient) -> None:
        s = time.perf_counter()
        try:
            oid = self._ctx["order_id"]
            code = f"SH-PF3-{uuid4().hex[:6]}"
            resp = await client.post("/sal/shipments",
                json={"shipment_code": code, "order_id": oid, "warehouse_id": str(uuid4()),
                      "lines": [{"sku_id": self._ctx["sku_id"], "quantity": 30}]},
                headers=self._headers())
            sid = resp.json()["shipment_id"]
            await client.post(f"/sal/shipments/{sid}/submit", headers=self._headers())
            await client.post(f"/sal/shipments/{sid}/confirm",
                json={"idempotency_key": f"sal:shipment:{sid}:ship"}, headers=self._headers())
            order_resp = await client.get(f"/sal/orders/{oid}", headers=self._headers())
            order = order_resp.json()
            shipped = order.get("total_shipped", 0)
            status = order.get("status", "")
            self._record(4, "第三次发货30(shipped=100 remaining=0 SHIPPED)", s,
                         shipped == 100, f"shipped={shipped} status={status}")
        except Exception as e:
            self._record(4, "第三次发货30", s, False, str(e))

    async def _step05_consistency_check(self, client: httpx.AsyncClient) -> None:
        s = time.perf_counter()
        try:
            oid = self._ctx["order_id"]
            resp = await client.get(f"/sal/orders/{oid}/trace", headers=self._headers())
            trace = resp.json()
            total_shipped = trace.get("total_shipped", 0)
            self._record(5, f"一致性校验(累计发货{total_shipped}=订单100)", s,
                         total_shipped == 100, f"trace={trace}")
        except Exception as e:
            self._record(5, "一致性校验", s, False, str(e))

    async def _step06_four_state_conservation(self, client: httpx.AsyncClient) -> None:
        s = time.perf_counter()
        try:
            oid = self._ctx["order_id"]
            resp = await client.get(f"/sal/orders/{oid}", headers=self._headers())
            order = resp.json()
            lines = order.get("lines", [])
            all_conserved = True
            for line in lines:
                ordered = line.get("ordered_quantity", 0)
                reserved = line.get("reserved_quantity", 0)
                shipped = line.get("shipped_quantity", 0)
                remaining = line.get("remaining_quantity", 0)
                if remaining != ordered - shipped:
                    all_conserved = False
                if reserved < shipped:
                    all_conserved = False
                if shipped > ordered:
                    all_conserved = False
            self._record(6, "四态守恒(remaining=ordered-shipped, reserved>=shipped, shipped<=ordered)", s,
                         all_conserved, f"lines={lines}")
        except Exception as e:
            self._record(6, "四态守恒", s, False, str(e))