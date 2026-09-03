"""FIN 采购订单只读视图 - PurOrderReadView（引用 PUR-001，禁止修改）。"""

from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class PurOrderReadView:
    """采购订单只读查询 - 仅用于结算校验，不修改 PUR 聚合。"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def query(self, order_no: str) -> dict[str, Any] | None:
        result = await self._session.execute(
            text(
                "SELECT order_no, supplier_id, status, total_amount, "
                "received_qty, is_fully_received "
                "FROM pur_order WHERE order_no = :order_no"
            ),
            {"order_no": order_no},
        )
        row = result.first()
        if row is None:
            return None
        return dict(row._mapping)

    async def get_received_quantity(self, order_no: str, product_id: str) -> Any:
        result = await self._session.execute(
            text(
                "SELECT received_qty FROM pur_order_line "
                "WHERE order_no = :order_no AND product_id = :product_id"
            ),
            {"order_no": order_no, "product_id": product_id},
        )
        row = result.first()
        return row[0] if row else None