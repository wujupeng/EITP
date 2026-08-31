"""治理工作流与版本管理仓储 - GovernanceWorkflow/MasterDataVersion/NegativeInventoryPolicyAudit/MasterDataAudit。

版本与审计表 append-only 不可变（仅 INSERT/SELECT）。
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.mdm.models import (
    AttributeTemplateORM,
    GovernanceWorkflowORM,
    MasterDataAuditORM,
    MasterDataVersionORM,
    NegativeInventoryPolicyAuditORM,
    SpecTemplateORM,
)


class SpecTemplateRepository:
    """规格模板仓储。"""

    async def save(self, session: AsyncSession, agg) -> SpecTemplateORM:
        orm = SpecTemplateORM(
            template_id=agg.id.value,
            tenant_id=agg.tenant_id,
            template_level=agg.template_level.value,
            template_code=agg.template_code,
            template_name=agg.template_name,
            attribute_definitions=[
                {
                    "attribute_name": a.attribute_name,
                    "attribute_type": a.attribute_type.value,
                    "is_required": a.is_required,
                    "enum_values": a.enum_values,
                    "min_value": a.min_value,
                    "max_value": a.max_value,
                }
                for a in agg.attribute_definitions
            ],
            status=agg.status.value,
        )
        session.add(orm)
        await session.flush()
        return orm

    async def get_by_id(self, session: AsyncSession, template_id: UUID) -> SpecTemplateORM | None:
        stmt = select(SpecTemplateORM).where(SpecTemplateORM.template_id == template_id)
        return (await session.execute(stmt)).scalar_one_or_none()

    async def get_by_code(self, session: AsyncSession, code: str, tenant_id: UUID | None = None) -> SpecTemplateORM | None:
        stmt = select(SpecTemplateORM).where(SpecTemplateORM.template_code == code)
        if tenant_id is not None:
            stmt = stmt.where(SpecTemplateORM.tenant_id == tenant_id)
        return (await session.execute(stmt)).scalar_one_or_none()

    async def list_all(self, session: AsyncSession, tenant_id: UUID | None = None) -> list[SpecTemplateORM]:
        stmt = select(SpecTemplateORM)
        if tenant_id is not None:
            stmt = stmt.where(SpecTemplateORM.tenant_id == tenant_id)
        return list((await session.execute(stmt)).scalars().all())


class AttributeTemplateRepository:
    """属性模板仓储。"""

    async def save(self, session: AsyncSession, agg) -> AttributeTemplateORM:
        orm = AttributeTemplateORM(
            template_id=agg.id.value,
            tenant_id=agg.tenant_id,
            template_level=agg.template_level.value,
            template_code=agg.template_code,
            template_name=agg.template_name,
            attribute_name=agg.attribute_name,
            attribute_type=agg.attribute_type.value,
            enum_values=agg.enum_values,
            is_required=agg.is_required,
            status=agg.status.value,
        )
        session.add(orm)
        await session.flush()
        return orm

    async def get_by_id(self, session: AsyncSession, template_id: UUID) -> AttributeTemplateORM | None:
        stmt = select(AttributeTemplateORM).where(AttributeTemplateORM.template_id == template_id)
        return (await session.execute(stmt)).scalar_one_or_none()

    async def list_all(self, session: AsyncSession, tenant_id: UUID | None = None) -> list[AttributeTemplateORM]:
        stmt = select(AttributeTemplateORM)
        if tenant_id is not None:
            stmt = stmt.where(AttributeTemplateORM.tenant_id == tenant_id)
        return list((await session.execute(stmt)).scalars().all())


class GovernanceWorkflowRepository:
    """治理工作流仓储。"""

    async def save(self, session: AsyncSession, agg) -> GovernanceWorkflowORM:
        orm = GovernanceWorkflowORM(
            request_id=agg.id.value,
            tenant_id=agg.tenant_id,
            governance_level=agg.governance_level.value,
            entity_type=agg.entity_type,
            entity_id=agg.entity_id,
            target_version_id=agg.target_version_id,
            status=agg.status.value,
            submitted_by=agg.submitted_by,
            submitted_at=agg.submitted_at,
            approved_by=agg.approved_by,
            approved_at=agg.approved_at,
            approval_opinion=agg.approval_opinion,
            published_by=agg.published_by,
            published_at=agg.published_at,
            rollback_by=agg.rollback_by,
            rollback_at=agg.rollback_at,
            rollback_reason=agg.rollback_reason,
        )
        session.add(orm)
        await session.flush()
        return orm

    async def get_by_id(self, session: AsyncSession, request_id: UUID) -> GovernanceWorkflowORM | None:
        stmt = select(GovernanceWorkflowORM).where(GovernanceWorkflowORM.request_id == request_id)
        return (await session.execute(stmt)).scalar_one_or_none()

    async def update(self, session: AsyncSession, agg) -> GovernanceWorkflowORM | None:
        orm = await self.get_by_id(session, agg.id.value)
        if orm is None:
            return None
        orm.status = agg.status.value
        orm.submitted_by = agg.submitted_by
        orm.submitted_at = agg.submitted_at
        orm.approved_by = agg.approved_by
        orm.approved_at = agg.approved_at
        orm.approval_opinion = agg.approval_opinion
        orm.published_by = agg.published_by
        orm.published_at = agg.published_at
        orm.rollback_by = agg.rollback_by
        orm.rollback_at = agg.rollback_at
        orm.rollback_reason = agg.rollback_reason
        await session.flush()
        return orm

    async def list_by_tenant(self, session: AsyncSession, tenant_id: UUID, offset: int = 0, limit: int = 50) -> list[GovernanceWorkflowORM]:
        stmt = select(GovernanceWorkflowORM).where(
            GovernanceWorkflowORM.tenant_id == tenant_id,
        ).offset(offset).limit(limit)
        return list((await session.execute(stmt)).scalars().all())

    async def list_pending(self, session: AsyncSession, offset: int = 0, limit: int = 50) -> list[GovernanceWorkflowORM]:
        stmt = select(GovernanceWorkflowORM).where(
            GovernanceWorkflowORM.status == "submitted",
        ).offset(offset).limit(limit)
        return list((await session.execute(stmt)).scalars().all())


class MasterDataVersionRepository:
    """主数据版本仓储 - append-only，仅 INSERT/SELECT。"""

    async def save(self, session: AsyncSession, agg) -> MasterDataVersionORM:
        orm = MasterDataVersionORM(
            version_id=agg.id.value,
            tenant_id=agg.tenant_id,
            entity_type=agg.entity_type,
            entity_id=agg.entity_id,
            version_number=agg.version_number,
            snapshot_before=agg.snapshot_before,
            snapshot_after=agg.snapshot_after,
            change_type=agg.change_type.value,
            operated_by=agg.operated_by,
            reason=agg.reason,
        )
        session.add(orm)
        await session.flush()
        return orm

    async def get_by_id(self, session: AsyncSession, version_id: UUID) -> MasterDataVersionORM | None:
        stmt = select(MasterDataVersionORM).where(MasterDataVersionORM.version_id == version_id)
        return (await session.execute(stmt)).scalar_one_or_none()

    async def list_by_entity(self, session: AsyncSession, entity_type: str, entity_id: UUID) -> list[MasterDataVersionORM]:
        stmt = select(MasterDataVersionORM).where(
            MasterDataVersionORM.entity_type == entity_type,
            MasterDataVersionORM.entity_id == entity_id,
        ).order_by(MasterDataVersionORM.version_number)
        return list((await session.execute(stmt)).scalars().all())


class NegativeInventoryPolicyAuditRepository:
    """负库存策略审计仓储 - append-only，仅 INSERT/SELECT。"""

    async def save(self, session: AsyncSession, agg) -> NegativeInventoryPolicyAuditORM:
        orm = NegativeInventoryPolicyAuditORM(
            audit_id=agg.audit_id,
            tenant_id=agg.tenant_id,
            policy_before=agg.policy_before.value,
            policy_after=agg.policy_after.value,
            operated_by=agg.operated_by,
            reason=agg.reason,
        )
        session.add(orm)
        await session.flush()
        return orm

    async def list_by_tenant(self, session: AsyncSession, tenant_id: UUID, offset: int = 0, limit: int = 50) -> list[NegativeInventoryPolicyAuditORM]:
        stmt = select(NegativeInventoryPolicyAuditORM).where(
            NegativeInventoryPolicyAuditORM.tenant_id == tenant_id,
        ).order_by(NegativeInventoryPolicyAuditORM.operated_at.desc()).offset(offset).limit(limit)
        return list((await session.execute(stmt)).scalars().all())


class MasterDataAuditRepository:
    """主数据审计仓储 - append-only，仅 INSERT/SELECT。"""

    async def save(self, session: AsyncSession, agg) -> MasterDataAuditORM:
        orm = MasterDataAuditORM(
            audit_id=agg.audit_id,
            tenant_id=agg.tenant_id,
            action=agg.action.value,
            entity_type=agg.entity_type,
            entity_id=agg.entity_id,
            version_number=agg.version_number,
            old_value=agg.old_value,
            new_value=agg.new_value,
            operated_by=agg.operated_by,
            reason=agg.reason,
            ip_address=agg.ip_address,
        )
        session.add(orm)
        await session.flush()
        return orm

    async def list_by_entity(self, session: AsyncSession, entity_type: str, entity_id: str, offset: int = 0, limit: int = 50) -> list[MasterDataAuditORM]:
        stmt = select(MasterDataAuditORM).where(
            MasterDataAuditORM.entity_type == entity_type,
            MasterDataAuditORM.entity_id == entity_id,
        ).order_by(MasterDataAuditORM.operated_at.desc()).offset(offset).limit(limit)
        return list((await session.execute(stmt)).scalars().all())

    async def list_by_tenant(self, session: AsyncSession, tenant_id: UUID, offset: int = 0, limit: int = 50) -> list[MasterDataAuditORM]:
        stmt = select(MasterDataAuditORM).where(
            MasterDataAuditORM.tenant_id == tenant_id,
        ).order_by(MasterDataAuditORM.operated_at.desc()).offset(offset).limit(limit)
        return list((await session.execute(stmt)).scalars().all())