"""ApprovalFlowRepository - 审批流仓储。"""

from __future__ import annotations

import json
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.biz_ops.aggregates.approval_flow_aggregate import ApprovalFlowAggregate
from app.domain.biz_ops.enums.enums import RoutingStrategyType, TimeoutStrategy
from app.domain.biz_ops.value_objects.approval_node import ApprovalNode
from app.domain.shared.entity import EntityId
from app.infrastructure.biz_ops.models import (
    BizOpsApprovalFlowORM,
    BizOpsApprovalNodeORM,
    BizOpsApprovalRecordORM,
)


class ApprovalFlowRepository:
    """审批流仓储。"""

    async def create_flow(self, session: AsyncSession, agg: ApprovalFlowAggregate) -> BizOpsApprovalFlowORM:
        orm = BizOpsApprovalFlowORM(
            id=agg.id.value, tenant_id=agg.tenant_id, flow_key=agg.flow_key,
            flow_name=agg.flow_name, entity_type=agg.entity_type,
            is_active="true" if agg.is_active else "false",
            version=agg.version, description=agg.description,
        )
        session.add(orm)
        for node in agg.nodes:
            node_orm = BizOpsApprovalNodeORM(
                id=EntityId.generate().value, tenant_id=agg.tenant_id, flow_id=agg.id.value,
                node_order=node.node_order, node_name=node.node_name,
                routing_strategy=node.routing_strategy.value,
                routing_config=json.dumps(node.routing_config),
                timeout_seconds=node.timeout_seconds,
                timeout_strategy=node.timeout_strategy.value,
                is_countersign="true" if node.is_countersign else "false",
                countersign_ratio=node.countersign_ratio,
                condition_expression=node.condition_expression,
            )
            session.add(node_orm)
        await session.flush()
        return orm

    async def get_by_key(self, session: AsyncSession, tenant_id: UUID, flow_key: str) -> BizOpsApprovalFlowORM | None:
        stmt = select(BizOpsApprovalFlowORM).where(
            BizOpsApprovalFlowORM.tenant_id == tenant_id,
            BizOpsApprovalFlowORM.flow_key == flow_key,
        )
        return (await session.execute(stmt)).scalar_one_or_none()

    async def list_by_tenant(self, session: AsyncSession, tenant_id: UUID) -> list[BizOpsApprovalFlowORM]:
        stmt = select(BizOpsApprovalFlowORM).where(BizOpsApprovalFlowORM.tenant_id == tenant_id)
        return list((await session.execute(stmt)).scalars().all())

    async def get_nodes(self, session: AsyncSession, flow_id: UUID) -> list[BizOpsApprovalNodeORM]:
        stmt = select(BizOpsApprovalNodeORM).where(
            BizOpsApprovalNodeORM.flow_id == flow_id
        ).order_by(BizOpsApprovalNodeORM.node_order)
        return list((await session.execute(stmt)).scalars().all())

    async def add_record(self, session: AsyncSession, tenant_id: UUID, approval_id: UUID, flow_id: UUID, node_order: int, action: str, operator_id: UUID, comment: str = "") -> BizOpsApprovalRecordORM:
        orm = BizOpsApprovalRecordORM(
            id=EntityId.generate().value, tenant_id=tenant_id, approval_id=approval_id,
            flow_id=flow_id, node_order=node_order, action=action, operator_id=operator_id, comment=comment,
        )
        session.add(orm)
        await session.flush()
        return orm

    def to_aggregate(self, flow_orm: BizOpsApprovalFlowORM, node_orms: list[BizOpsApprovalNodeORM]) -> ApprovalFlowAggregate:
        nodes = [
            ApprovalNode(
                node_order=n.node_order, node_name=n.node_name,
                routing_strategy=RoutingStrategyType(n.routing_strategy),
                routing_config=json.loads(n.routing_config) if n.routing_config else {},
                timeout_seconds=n.timeout_seconds,
                timeout_strategy=TimeoutStrategy(n.timeout_strategy),
                is_countersign=(n.is_countersign == "true"),
                countersign_ratio=n.countersign_ratio,
                condition_expression=n.condition_expression,
            )
            for n in node_orms
        ]
        return ApprovalFlowAggregate(
            id=EntityId(flow_orm.id), tenant_id=flow_orm.tenant_id, flow_key=flow_orm.flow_key,
            flow_name=flow_orm.flow_name, entity_type=flow_orm.entity_type,
            nodes=nodes, is_active=(flow_orm.is_active == "true"),
            version=flow_orm.version, description=flow_orm.description,
        )