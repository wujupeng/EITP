"""FIN 发票匹配引擎 - InvoiceMatchingEngine 多维度匹配。"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from app.domain.fin.aggregates.invoice_aggregate import InvoiceAggregate
from app.domain.fin.value_objects.money import Money


@dataclass(frozen=True)
class MatchResult:
    """匹配结果 - 匹配分数与匹配的业务单据。"""

    matched: bool
    score: float
    business_ref_type: str | None
    business_ref_id: str | None
    matched_fields: tuple[str, ...]


class InvoiceMatchingEngine:
    """发票匹配引擎 - 按金额/数量/商品/购销方多维度匹配。"""

    @staticmethod
    def match(
        invoice: InvoiceAggregate,
        candidates: list[dict[str, Any]],
        tolerance: Decimal = Decimal("0.01"),
    ) -> list[MatchResult]:
        results: list[MatchResult] = []
        for cand in candidates:
            result = InvoiceMatchingEngine._match_single(
                invoice, cand, tolerance
            )
            results.append(result)
        return results

    @staticmethod
    def _match_single(
        invoice: InvoiceAggregate,
        candidate: dict[str, Any],
        tolerance: Decimal,
    ) -> MatchResult:
        score = 0.0
        matched_fields: list[str] = []
        inv_amount = invoice.tax_inclusive_amount.amount
        cand_amount = Decimal(str(candidate.get("amount", "0")))
        if abs(inv_amount - cand_amount) <= tolerance:
            score += 0.4
            matched_fields.append("amount")
        cand_qty = Decimal(str(candidate.get("total_quantity", "0")))
        inv_qty = sum(ln.quantity for ln in invoice.invoice_lines)
        if cand_qty > 0 and abs(inv_qty - cand_qty) <= tolerance:
            score += 0.2
            matched_fields.append("quantity")
        cand_products = set(candidate.get("product_ids", []))
        inv_products = {ln.product_id for ln in invoice.invoice_lines}
        if cand_products and inv_products == cand_products:
            score += 0.2
            matched_fields.append("products")
        elif cand_products and inv_products & cand_products:
            score += 0.1
            matched_fields.append("partial_products")
        buyer_name = invoice.buyer_info.get("name", "")
        cand_buyer = candidate.get("buyer_name", "")
        if buyer_name and cand_buyer and buyer_name == cand_buyer:
            score += 0.1
            matched_fields.append("buyer")
        seller_name = invoice.seller_info.get("name", "")
        cand_seller = candidate.get("seller_name", "")
        if seller_name and cand_seller and seller_name == cand_seller:
            score += 0.1
            matched_fields.append("seller")
        matched = score >= 0.8
        return MatchResult(
            matched=matched,
            score=score,
            business_ref_type=candidate.get("business_ref_type"),
            business_ref_id=candidate.get("business_ref_id"),
            matched_fields=tuple(matched_fields),
        )

    @staticmethod
    def best_match(
        invoice: InvoiceAggregate,
        candidates: list[dict[str, Any]],
        tolerance: Decimal = Decimal("0.01"),
    ) -> MatchResult | None:
        results = InvoiceMatchingEngine.match(invoice, candidates, tolerance)
        matched_results = [r for r in results if r.matched]
        if not matched_results:
            return None
        return max(matched_results, key=lambda r: r.score)