"""层级管理 API 接口 - /api/v1/tenant/hierarchy/*。"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.hierarchy.hierarchy_app_svc import HierarchyAppSvc
from app.domain.hierarchy.hierarchy_node import HierarchyLevel
from app.infrastructure.db.session import get_db_session
from app.interfaces.schemas.hierarchy import (
    CreateNodeRequest,
    DisableNodeResponse,
    NodeResponse,
    TreeNodeResponse,
)

router = APIRouter(prefix="/tenant/hierarchy", tags=["hierarchy"])


@router.post("/nodes", response_model=NodeResponse, status_code=201)
async def create_node(
    req: CreateNodeRequest,
    session: AsyncSession = Depends(get_db_session),
) -> NodeResponse:
    """创建层级节点。"""
    svc = HierarchyAppSvc(session)
    node = await svc.create_node(
        level=HierarchyLevel(req.level),
        name=req.name,
        parent_id=req.parent_id,
    )
    return NodeResponse(
        id=node.id.value,
        tenant_id=node.tenant_id,
        level=node.level.value,
        name=node.name,
        parent_id=node.parent_id.value if node.parent_id else None,
        is_active=node.is_active,
    )


@router.get("/nodes/{node_id}", response_model=NodeResponse)
async def get_node(
    node_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> NodeResponse:
    """查询单个层级节点。"""
    svc = HierarchyAppSvc(session)
    node = await svc.get_node(node_id)
    if node is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="节点不存在")
    return NodeResponse(
        id=node.id.value,
        tenant_id=node.tenant_id,
        level=node.level.value,
        name=node.name,
        parent_id=node.parent_id.value if node.parent_id else None,
        is_active=node.is_active,
    )


@router.get("/tree", response_model=list[TreeNodeResponse])
async def get_tree(
    root_id: UUID | None = Query(default=None),
    session: AsyncSession = Depends(get_db_session),
) -> list[TreeNodeResponse]:
    """查询层级树。"""
    svc = HierarchyAppSvc(session)
    nodes = await svc.get_tree(root_id)
    return [
        TreeNodeResponse(
            id=n.id.value,
            tenant_id=n.tenant_id,
            level=n.level.value,
            name=n.name,
            parent_id=n.parent_id.value if n.parent_id else None,
            is_active=n.is_active,
            children=[],
        )
        for n in nodes
    ]


@router.patch("/nodes/{node_id}/disable", response_model=DisableNodeResponse)
async def disable_node(
    node_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> DisableNodeResponse:
    """停用层级节点（级联停用下级）。"""
    svc = HierarchyAppSvc(session)
    node = await svc.disable_node(node_id)
    if node is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="节点不存在")
    return DisableNodeResponse(node_id=node_id, disabled_count=1)