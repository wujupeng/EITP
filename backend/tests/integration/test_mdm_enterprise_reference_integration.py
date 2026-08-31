"""EITP-MDM-001-T16-06 企业商品引用与定制集成测试。

跨模块调用 EnterpriseProductAppSvc + ProductReferenceAppSvc + EnterpriseCustomizationAppSvc，
验证：查询可引用集团商品 → 引用集团商品自动创建企业 SKU → 创建定制变更申请
→ 审批发布 → 发布 EnterpriseCustomizationPublishedEvent 全流程。

对应 spec 5.2.1.2 / 5.2.1.4 / 5.2.3.5 / 5.7.1.8，design 2.5.2。
"""

from __future__ import annotations

from contextlib import contextmanager
from decimal import Decimal
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest

from app.application.enterprise_product.enterprise_customization_app_svc import (
    EnterpriseCustomizationAppSvc,
)
from app.application.enterprise_product.enterprise_product_app_svc import (
    EnterpriseProductAppSvc,
)
from app.application.enterprise_product.product_reference_app_svc import (
    ProductReferenceAppSvc,
)
from app.domain.enterprise_product.aggregates.enterprise_product_aggregate import (
    EnterpriseProductAggregate,
    ReferenceStatus,
)
from app.domain.enterprise_product.aggregates.product_customization_aggregate import (
    CostModelType,
    InventoryStrategy,
    ProductCustomizationAggregate,
)
from app.domain.enterprise_product.aggregates.product_reference_aggregate import (
    ProductReferenceAggregate,
)
from app.domain.enterprise_product.entities.enterprise_sku import (
    EnterpriseSku,
    EnterpriseSkuStatus,
)
from app.domain.enterprise_product.events.enterprise_product_events import (
    EnterpriseCustomizationPublishedEvent,
    EnterpriseProductReferencedEvent,
    EnterpriseReferenceReleasedEvent,
)
from app.domain.group_catalog.aggregates.group_product_aggregate import (
    GroupProductAggregate,
    GroupProductStatus,
)
from app.domain.shared.entity import EntityId
from app.interfaces.middleware.error_handler import MDMError, MDMErrorCode
from app.interfaces.middleware.security_context import (
    PermissionSummary,
    ResolvedDataScope,
    RoleSummary,
    SecurityContext,
    TenantIdentity,
    UserIdentity,
)


# ----------------------------- 测试替身 -----------------------------


class _DummySession:
    async def flush(self) -> None:
        return None

    async def commit(self) -> None:
        return None

    async def rollback(self) -> None:
        return None

    def add(self, _orm: object) -> None:
        return None


class _GroupProductORMProxy:
    """集团商品 ORM 代理。"""

    def __init__(
        self,
        group_product_id: UUID,
        group_product_code: str,
        group_product_name: str,
        base_unit_id: UUID,
        group_category_id: UUID | None = None,
        group_brand_id: UUID | None = None,
        spec_template_id: UUID | None = None,
        description: str | None = None,
        status: str = GroupProductStatus.ACTIVE.value,
        published_version: int = 1,
    ) -> None:
        self.group_product_id = group_product_id
        self.group_product_code = group_product_code
        self.group_product_name = group_product_name
        self.base_unit_id = base_unit_id
        self.group_category_id = group_category_id
        self.group_brand_id = group_brand_id
        self.spec_template_id = spec_template_id
        self.description = description
        self.status = status
        self.published_version = published_version


class _GroupSkuORMProxy:
    """集团 SKU ORM 代理。"""

    def __init__(
        self,
        group_sku_id: UUID,
        group_sku_code: str,
        group_sku_name: str,
        barcode_list: list[str] | None = None,
    ) -> None:
        self.group_sku_id = group_sku_id
        self.group_sku_code = group_sku_code
        self.group_sku_name = group_sku_name
        self.barcode_list = barcode_list


class _EnterpriseProductORMProxy:
    """企业商品 ORM 代理（可变，支持 release_reference 回写）。"""

    def __init__(self, agg: EnterpriseProductAggregate) -> None:
        self.enterprise_product_id = agg.id.value
        self.tenant_id = agg.tenant_id
        self.group_product_id = agg.group_product_id
        self.enterprise_product_code = agg.enterprise_product_code
        self.enterprise_product_name = agg.enterprise_product_name
        self.enterprise_category_id = agg.enterprise_category_id
        self.reference_status = agg.reference_status.value
        self.published_version = agg.published_version


class _ProductReferenceORMProxy:
    """商品引用关系 ORM 代理。"""

    def __init__(
        self,
        tenant_id: UUID,
        group_product_id: UUID,
        enterprise_product_id: UUID,
        reference_status: str = ReferenceStatus.ACTIVE.value,
    ) -> None:
        self.tenant_id = tenant_id
        self.group_product_id = group_product_id
        self.enterprise_product_id = enterprise_product_id
        self.reference_status = reference_status


class _FakeGroupProductRepo:
    def __init__(self, products: dict[UUID, _GroupProductORMProxy] | None = None) -> None:
        self._store = dict(products) if products else {}

    async def get_by_id(self, session: object, group_product_id: UUID):
        return self._store.get(group_product_id)


class _FakeGroupSkuRepo:
    def __init__(self, skus_by_product: dict[UUID, list[_GroupSkuORMProxy]] | None = None) -> None:
        self._store = dict(skus_by_product) if skus_by_product else {}

    async def list_by_product(self, session: object, group_product_id: UUID):
        return list(self._store.get(group_product_id, []))


class _FakeEnterpriseProductRepo:
    def __init__(self) -> None:
        self._store: dict[tuple[UUID, UUID], _EnterpriseProductORMProxy] = {}

    async def save(self, session: object, agg: EnterpriseProductAggregate) -> None:
        self._store[(agg.tenant_id, agg.id.value)] = _EnterpriseProductORMProxy(agg)

    async def get_by_tenant_and_code(
        self, session: object, tenant_id: UUID, code: str
    ) -> _EnterpriseProductORMProxy | None:
        for (t, _pid), orm in self._store.items():
            if t == tenant_id and orm.enterprise_product_code == code:
                return orm
        return None

    async def get_by_id(
        self, session: object, tenant_id: UUID, enterprise_product_id: UUID
    ) -> _EnterpriseProductORMProxy | None:
        return self._store.get((tenant_id, enterprise_product_id))

    async def list_by_tenant(
        self, session: object, tenant_id: UUID, offset: int = 0, limit: int = 50
    ) -> list[_EnterpriseProductORMProxy]:
        items = [orm for (t, _pid), orm in self._store.items() if t == tenant_id]
        return items[offset : offset + limit]


class _FakeEnterpriseSkuRepo:
    def __init__(self) -> None:
        self.saved: list[EnterpriseSku] = []

    async def save(self, session: object, sku: EnterpriseSku) -> None:
        self.saved.append(sku)


class _FakeProductReferenceRepo:
    def __init__(self) -> None:
        self._store: list[_ProductReferenceORMProxy] = []

    async def save(self, session: object, ref_agg) -> None:
        self._store.append(
            _ProductReferenceORMProxy(
                tenant_id=ref_agg.tenant_id,
                group_product_id=ref_agg.group_product_id,
                enterprise_product_id=ref_agg.enterprise_product_id,
                reference_status=ref_agg.reference_status.value,
            )
        )

    async def list_by_tenant(self, session: object, tenant_id: UUID):
        return [r for r in self._store if r.tenant_id == tenant_id]

    async def list_by_group_product(self, session: object, group_product_id: UUID):
        return [r for r in self._store if r.group_product_id == group_product_id]


class _FakeCustomizationRepo:
    def __init__(self) -> None:
        self._store: dict[tuple[UUID, UUID], ProductCustomizationAggregate] = {}

    async def save(self, session: object, agg: ProductCustomizationAggregate) -> None:
        self._store[(agg.tenant_id, agg.enterprise_product_id)] = agg

    async def get_by_product(
        self, session: object, tenant_id: UUID, enterprise_product_id: UUID
    ) -> ProductCustomizationAggregate | None:
        return self._store.get((tenant_id, enterprise_product_id))


# ----------------------------- 公共辅助 -----------------------------


_ENTERPRISE_MANAGE = "mdm:enterprise_product:manage"


def _make_ctx(
    tenant_id: UUID,
    permissions: frozenset[str] = frozenset(),
    is_platform_admin: bool = False,
    is_tenant_admin: bool = True,
) -> SecurityContext:
    return SecurityContext(
        user=UserIdentity(
            user_id=uuid4(),
            username="enterprise-admin",
            is_platform_admin=is_platform_admin,
            is_tenant_admin=is_tenant_admin,
        ),
        tenant=TenantIdentity(tenant_id=tenant_id),
        roles=(RoleSummary(role_id=uuid4(), role_code="enterprise_admin", role_name="企业管理员"),),
        permissions=PermissionSummary(codes=permissions),
        data_scope=ResolvedDataScope(scope_type="tenant"),
    )


@contextmanager
def _apply_ctx(ctx: SecurityContext):
    token = SecurityContext.set(ctx)
    try:
        yield
    finally:
        SecurityContext.reset(token)


def _make_group_product(
    group_product_id: UUID | None = None,
    code: str = "GP-001",
    name: str = "集团商品A",
    status: str = GroupProductStatus.ACTIVE.value,
    published_version: int = 1,
) -> tuple[_GroupProductORMProxy, UUID]:
    gp_id = group_product_id or uuid4()
    orm = _GroupProductORMProxy(
        group_product_id=gp_id,
        group_product_code=code,
        group_product_name=name,
        base_unit_id=uuid4(),
        status=status,
        published_version=published_version,
    )
    return orm, gp_id


def _make_group_skus(group_product_id: UUID, count: int = 2) -> list[_GroupSkuORMProxy]:
    return [
        _GroupSkuORMProxy(
            group_sku_id=uuid4(),
            group_sku_code=f"GS-{idx:03d}",
            group_sku_name=f"集团SKU-{idx}",
            barcode_list=[f"69000000000{idx}"],
        )
        for idx in range(1, count + 1)
    ]


def _new_enterprise_product_svc(
    group_products: dict[UUID, _GroupProductORMProxy] | None = None,
    group_skus: dict[UUID, list[_GroupSkuORMProxy]] | None = None,
) -> tuple[
    EnterpriseProductAppSvc,
    _FakeEnterpriseProductRepo,
    _FakeEnterpriseSkuRepo,
    _FakeProductReferenceRepo,
]:
    session = _DummySession()
    svc = EnterpriseProductAppSvc(session=session)
    ep_repo = _FakeEnterpriseProductRepo()
    esku_repo = _FakeEnterpriseSkuRepo()
    ref_repo = _FakeProductReferenceRepo()
    gp_repo = _FakeGroupProductRepo(products=group_products)
    gsku_repo = _FakeGroupSkuRepo(skus_by_product=group_skus)
    svc._ep_repo = ep_repo
    svc._esku_repo = esku_repo
    svc._ref_repo = ref_repo
    svc._gp_repo = gp_repo
    svc._gsku_repo = gsku_repo
    return svc, ep_repo, esku_repo, ref_repo


def _new_reference_svc(
    ref_repo: _FakeProductReferenceRepo,
) -> ProductReferenceAppSvc:
    svc = ProductReferenceAppSvc(session=_DummySession())
    svc._repo = ref_repo
    return svc


def _new_customization_svc() -> tuple[
    EnterpriseCustomizationAppSvc, _FakeCustomizationRepo
]:
    svc = EnterpriseCustomizationAppSvc(session=_DummySession())
    repo = _FakeCustomizationRepo()
    svc._repo = repo
    return svc, repo


# ----------------------------- 集成测试 -----------------------------


class TestEnterpriseReferenceIntegration:
    """T16-06: 企业商品引用集成测试 - 引用集团商品自动创建企业 SKU。"""

    async def test_reference_auto_creates_enterprise_product_and_skus(self) -> None:
        """引用集团商品自动创建企业商品与企业 SKU（spec 5.2.1.2）。"""
        tenant_id = uuid4()
        gp_orm, gp_id = _make_group_product()
        group_skus = _make_group_skus(gp_id, count=2)

        svc, ep_repo, esku_repo, _ = _new_enterprise_product_svc(
            group_products={gp_id: gp_orm},
            group_skus={gp_id: group_skus},
        )

        with _apply_ctx(_make_ctx(tenant_id, permissions=frozenset({_ENTERPRISE_MANAGE}))):
            ep_agg = await svc.reference_group_product(
                tenant_id=tenant_id,
                group_product_id=gp_id,
                enterprise_product_code="EP-001",
            )

        assert ep_agg.tenant_id == tenant_id
        assert ep_agg.group_product_id == gp_id
        assert ep_agg.reference_status == ReferenceStatus.ACTIVE
        # 企业 SKU 数量等于集团 SKU 数量
        assert len(esku_repo.saved) == 2
        assert all(s.tenant_id == tenant_id for s in esku_repo.saved)

    async def test_reference_inherits_group_sku_code_and_barcode(self) -> None:
        """企业 SKU 继承集团 SKU 编码与条码（spec 5.2.1.2）。"""
        tenant_id = uuid4()
        gp_orm, gp_id = _make_group_product()
        group_skus = _make_group_skus(gp_id, count=1)

        svc, _, esku_repo, _ = _new_enterprise_product_svc(
            group_products={gp_id: gp_orm},
            group_skus={gp_id: group_skus},
        )

        with _apply_ctx(_make_ctx(tenant_id, permissions=frozenset({_ENTERPRISE_MANAGE}))):
            await svc.reference_group_product(
                tenant_id=tenant_id,
                group_product_id=gp_id,
                enterprise_product_code="EP-INH",
            )

        esku = esku_repo.saved[0]
        assert esku.enterprise_sku_code == "GS-001"
        assert esku.enterprise_barcode_list == ["690000000001"]

    async def test_reference_publishes_enterprise_product_referenced_event(self) -> None:
        """引用集团商品发布 EnterpriseProductReferencedEvent。"""
        tenant_id = uuid4()
        gp_orm, gp_id = _make_group_product()
        group_skus = _make_group_skus(gp_id, count=1)

        svc, _, _, _ = _new_enterprise_product_svc(
            group_products={gp_id: gp_orm},
            group_skus={gp_id: group_skus},
        )

        with _apply_ctx(_make_ctx(tenant_id, permissions=frozenset({_ENTERPRISE_MANAGE}))):
            ep_agg = await svc.reference_group_product(
                tenant_id=tenant_id,
                group_product_id=gp_id,
                enterprise_product_code="EP-EVT",
            )

        events = list(ep_agg.pull_events())
        assert len(events) == 1
        event = events[0]
        assert isinstance(event, EnterpriseProductReferencedEvent)
        assert event.tenant_id == tenant_id
        assert event.group_product_id == gp_id

    async def test_reference_inherits_group_name_when_name_empty(self) -> None:
        """企业商品名称为空时继承集团商品名称。"""
        tenant_id = uuid4()
        gp_orm, gp_id = _make_group_product(name="集团商品名称X")
        group_skus = _make_group_skus(gp_id, count=1)

        svc, _, _, _ = _new_enterprise_product_svc(
            group_products={gp_id: gp_orm},
            group_skus={gp_id: group_skus},
        )

        with _apply_ctx(_make_ctx(tenant_id, permissions=frozenset({_ENTERPRISE_MANAGE}))):
            ep_agg = await svc.reference_group_product(
                tenant_id=tenant_id,
                group_product_id=gp_id,
                enterprise_product_code="EP-NAME",
            )

        assert ep_agg.enterprise_product_name == "集团商品名称X"

    async def test_duplicate_reference_rejected(self) -> None:
        """同一企业重复引用同一集团商品被拒绝（spec 5.2.3.5）。"""
        tenant_id = uuid4()
        gp_orm, gp_id = _make_group_product()
        group_skus = _make_group_skus(gp_id, count=1)

        svc, _, _, _ = _new_enterprise_product_svc(
            group_products={gp_id: gp_orm},
            group_skus={gp_id: group_skus},
        )

        with _apply_ctx(_make_ctx(tenant_id, permissions=frozenset({_ENTERPRISE_MANAGE}))):
            await svc.reference_group_product(
                tenant_id=tenant_id,
                group_product_id=gp_id,
                enterprise_product_code="EP-DUP-1",
            )
            with pytest.raises(MDMError) as exc:
                await svc.reference_group_product(
                    tenant_id=tenant_id,
                    group_product_id=gp_id,
                    enterprise_product_code="EP-DUP-2",
                )
        assert exc.value.code == MDMErrorCode.DUPLICATE_REFERENCE

    async def test_duplicate_enterprise_product_code_rejected(self) -> None:
        """同租户企业商品编码重复被拒绝。"""
        tenant_id = uuid4()
        gp_orm_1, gp_id_1 = _make_group_product(code="GP-A")
        gp_orm_2, gp_id_2 = _make_group_product(code="GP-B")
        group_skus = _make_group_skus(gp_id_1, count=1)

        svc, _, _, _ = _new_enterprise_product_svc(
            group_products={gp_id_1: gp_orm_1, gp_id_2: gp_orm_2},
            group_skus={gp_id_1: group_skus, gp_id_2: _make_group_skus(gp_id_2, count=1)},
        )

        with _apply_ctx(_make_ctx(tenant_id, permissions=frozenset({_ENTERPRISE_MANAGE}))):
            await svc.reference_group_product(
                tenant_id=tenant_id,
                group_product_id=gp_id_1,
                enterprise_product_code="EP-SAME",
            )
            with pytest.raises(MDMError) as exc:
                await svc.reference_group_product(
                    tenant_id=tenant_id,
                    group_product_id=gp_id_2,
                    enterprise_product_code="EP-SAME",
                )
        assert exc.value.code == MDMErrorCode.DUPLICATE_REFERENCE

    async def test_reference_unpublished_group_product_rejected(self) -> None:
        """引用未发布集团商品被拒绝（spec 5.7.1.8）。"""
        tenant_id = uuid4()
        gp_orm, gp_id = _make_group_product(published_version=0)
        group_skus = _make_group_skus(gp_id, count=1)

        svc, _, _, _ = _new_enterprise_product_svc(
            group_products={gp_id: gp_orm},
            group_skus={gp_id: group_skus},
        )

        with _apply_ctx(_make_ctx(tenant_id, permissions=frozenset({_ENTERPRISE_MANAGE}))):
            with pytest.raises(MDMError) as exc:
                await svc.reference_group_product(
                    tenant_id=tenant_id,
                    group_product_id=gp_id,
                    enterprise_product_code="EP-UNP",
                )
        assert exc.value.code == MDMErrorCode.GROUP_PRODUCT_NOT_PUBLISHED

    async def test_reference_disabled_group_product_rejected(self) -> None:
        """引用已停用集团商品被拒绝（spec 5.7.1.8）。"""
        tenant_id = uuid4()
        gp_orm, gp_id = _make_group_product(status=GroupProductStatus.DISABLED.value)
        group_skus = _make_group_skus(gp_id, count=1)

        svc, _, _, _ = _new_enterprise_product_svc(
            group_products={gp_id: gp_orm},
            group_skus={gp_id: group_skus},
        )

        with _apply_ctx(_make_ctx(tenant_id, permissions=frozenset({_ENTERPRISE_MANAGE}))):
            with pytest.raises(MDMError) as exc:
                await svc.reference_group_product(
                    tenant_id=tenant_id,
                    group_product_id=gp_id,
                    enterprise_product_code="EP-DIS",
                )
        assert exc.value.code == MDMErrorCode.GROUP_PRODUCT_DISABLED

    async def test_cross_tenant_reference_rejected(self) -> None:
        """跨租户引用（安全上下文租户与目标租户不一致）被拒绝。"""
        tenant_a = uuid4()
        tenant_b = uuid4()
        gp_orm, gp_id = _make_group_product()
        group_skus = _make_group_skus(gp_id, count=1)

        svc, _, _, _ = _new_enterprise_product_svc(
            group_products={gp_id: gp_orm},
            group_skus={gp_id: group_skus},
        )

        # 安全上下文为租户 A，尝试为租户 B 创建引用
        with _apply_ctx(_make_ctx(tenant_a, permissions=frozenset({_ENTERPRISE_MANAGE}))):
            with pytest.raises(MDMError) as exc:
                await svc.reference_group_product(
                    tenant_id=tenant_b,
                    group_product_id=gp_id,
                    enterprise_product_code="EP-CROSS",
                )
        assert exc.value.code == MDMErrorCode.CROSS_TENANT_POLICY_DENIED

    async def test_reference_without_security_context_rejected(self) -> None:
        """未认证引用被拒绝。"""
        tenant_id = uuid4()
        gp_orm, gp_id = _make_group_product()
        group_skus = _make_group_skus(gp_id, count=1)

        svc, _, _, _ = _new_enterprise_product_svc(
            group_products={gp_id: gp_orm},
            group_skus={gp_id: group_skus},
        )

        with pytest.raises(MDMError) as exc:
            await svc.reference_group_product(
                tenant_id=tenant_id,
                group_product_id=gp_id,
                enterprise_product_code="EP-NOCTX",
            )
        assert exc.value.code == MDMErrorCode.DIRECT_ACCESS_DENIED

    async def test_release_reference_preserves_inventory(self) -> None:
        """解除引用标记 reference_released，保留存量库存（spec 5.2.1.6）。"""
        tenant_id = uuid4()
        gp_orm, gp_id = _make_group_product()
        group_skus = _make_group_skus(gp_id, count=1)

        svc, ep_repo, _, _ = _new_enterprise_product_svc(
            group_products={gp_id: gp_orm},
            group_skus={gp_id: group_skus},
        )

        with _apply_ctx(_make_ctx(tenant_id, permissions=frozenset({_ENTERPRISE_MANAGE}))):
            ep_agg = await svc.reference_group_product(
                tenant_id=tenant_id,
                group_product_id=gp_id,
                enterprise_product_code="EP-REL",
            )
            ep_id = ep_agg.id.value

            released = await svc.release_reference(
                tenant_id=tenant_id, enterprise_product_id=ep_id
            )

        assert released.reference_status == ReferenceStatus.REFERENCE_RELEASED
        # 仓储中企业商品仍存在（存量保留），仅状态变更
        orm = await ep_repo.get_by_id(None, tenant_id, ep_id)
        assert orm is not None
        assert orm.reference_status == ReferenceStatus.REFERENCE_RELEASED.value

    async def test_release_reference_publishes_released_event(self) -> None:
        """解除引用发布 EnterpriseReferenceReleasedEvent。"""
        tenant_id = uuid4()
        gp_orm, gp_id = _make_group_product()
        group_skus = _make_group_skus(gp_id, count=1)

        svc, _, _, _ = _new_enterprise_product_svc(
            group_products={gp_id: gp_orm},
            group_skus={gp_id: group_skus},
        )

        with _apply_ctx(_make_ctx(tenant_id, permissions=frozenset({_ENTERPRISE_MANAGE}))):
            ep_agg = await svc.reference_group_product(
                tenant_id=tenant_id,
                group_product_id=gp_id,
                enterprise_product_code="EP-RELV",
            )
            released = await svc.release_reference(
                tenant_id=tenant_id, enterprise_product_id=ep_agg.id.value
            )

        events = list(released.pull_events())
        assert len(events) == 1
        assert isinstance(events[0], EnterpriseReferenceReleasedEvent)
        assert events[0].group_product_id == gp_id


class TestProductReferenceQueryIntegration:
    """T16-06: 商品引用关系查询集成测试 - 集团视角/企业视角。"""

    async def test_list_references_by_group_product(self) -> None:
        """集团管理员视角：查询某集团商品被哪些企业引用。"""
        tenant_a = uuid4()
        tenant_b = uuid4()
        gp_orm, gp_id = _make_group_product()
        group_skus = _make_group_skus(gp_id, count=1)

        svc, _, _, ref_repo = _new_enterprise_product_svc(
            group_products={gp_id: gp_orm},
            group_skus={gp_id: group_skus},
        )

        with _apply_ctx(_make_ctx(tenant_a, permissions=frozenset({_ENTERPRISE_MANAGE}))):
            await svc.reference_group_product(
                tenant_id=tenant_a, group_product_id=gp_id, enterprise_product_code="EP-A"
            )
        with _apply_ctx(_make_ctx(tenant_b, permissions=frozenset({_ENTERPRISE_MANAGE}))):
            await svc.reference_group_product(
                tenant_id=tenant_b, group_product_id=gp_id, enterprise_product_code="EP-B"
            )

        ref_svc = _new_reference_svc(ref_repo)
        refs = await ref_svc.list_references_by_group_product(gp_id)
        assert len(refs) == 2
        ref_tenants = {r.tenant_id for r in refs}
        assert ref_tenants == {tenant_a, tenant_b}

    async def test_list_references_by_tenant(self) -> None:
        """企业管理员视角：查询本企业引用了哪些集团商品。"""
        tenant_id = uuid4()
        gp_orm_1, gp_id_1 = _make_group_product(code="GP-1")
        gp_orm_2, gp_id_2 = _make_group_product(code="GP-2")
        group_skus_1 = _make_group_skus(gp_id_1, count=1)
        group_skus_2 = _make_group_skus(gp_id_2, count=1)

        svc, _, _, ref_repo = _new_enterprise_product_svc(
            group_products={gp_id_1: gp_orm_1, gp_id_2: gp_orm_2},
            group_skus={gp_id_1: group_skus_1, gp_id_2: group_skus_2},
        )

        with _apply_ctx(_make_ctx(tenant_id, permissions=frozenset({_ENTERPRISE_MANAGE}))):
            await svc.reference_group_product(
                tenant_id=tenant_id, group_product_id=gp_id_1, enterprise_product_code="EP-1"
            )
            await svc.reference_group_product(
                tenant_id=tenant_id, group_product_id=gp_id_2, enterprise_product_code="EP-2"
            )

        ref_svc = _new_reference_svc(ref_repo)
        refs = await ref_svc.list_references_by_tenant(tenant_id)
        assert len(refs) == 2
        ref_groups = {r.group_product_id for r in refs}
        assert ref_groups == {gp_id_1, gp_id_2}


class TestEnterpriseCustomizationIntegration:
    """T16-06: 企业定制集成测试 - 创建定制并发布事件。"""

    async def test_create_customization_returns_aggregate(self) -> None:
        """创建企业定制返回聚合根，租户级隔离。"""
        tenant_id = uuid4()
        enterprise_product_id = uuid4()
        svc, repo = _new_customization_svc()

        with _apply_ctx(_make_ctx(tenant_id, permissions=frozenset({_ENTERPRISE_MANAGE}))):
            agg = await svc.create_customization(
                tenant_id=tenant_id,
                enterprise_product_id=enterprise_product_id,
                sales_price=Decimal("99.50"),
                purchase_price=Decimal("60.00"),
                inventory_strategy=InventoryStrategy.STRICT,
                safety_stock=Decimal("10"),
                cost_model=CostModelType.MOVING_AVERAGE,
                custom_attributes={"label": "促销品"},
            )

        assert agg.tenant_id == tenant_id
        assert agg.enterprise_product_id == enterprise_product_id
        assert agg.sales_price == Decimal("99.50")
        assert agg.cost_model == CostModelType.MOVING_AVERAGE
        assert agg.custom_attributes == {"label": "促销品"}
        stored = await repo.get_by_product(None, tenant_id, enterprise_product_id)
        assert stored is not None

    async def test_customization_cross_tenant_rejected(self) -> None:
        """跨租户创建定制被拒绝。"""
        tenant_a = uuid4()
        tenant_b = uuid4()
        svc, _ = _new_customization_svc()

        with _apply_ctx(_make_ctx(tenant_a, permissions=frozenset({_ENTERPRISE_MANAGE}))):
            with pytest.raises(MDMError) as exc:
                await svc.create_customization(
                    tenant_id=tenant_b,
                    enterprise_product_id=uuid4(),
                    sales_price=Decimal("10"),
                )
        assert exc.value.code == MDMErrorCode.CROSS_TENANT_POLICY_DENIED

    async def test_customization_without_security_context_rejected(self) -> None:
        """未认证创建定制被拒绝。"""
        svc, _ = _new_customization_svc()
        with pytest.raises(MDMError) as exc:
            await svc.create_customization(
                tenant_id=uuid4(),
                enterprise_product_id=uuid4(),
            )
        assert exc.value.code == MDMErrorCode.DIRECT_ACCESS_DENIED

    async def test_publish_customization_publishes_event(self) -> None:
        """定制发布发布 EnterpriseCustomizationPublishedEvent。"""
        tenant_id = uuid4()
        enterprise_product_id = uuid4()
        svc, _ = _new_customization_svc()

        with _apply_ctx(_make_ctx(tenant_id, permissions=frozenset({_ENTERPRISE_MANAGE}))):
            agg = await svc.create_customization(
                tenant_id=tenant_id,
                enterprise_product_id=enterprise_product_id,
                sales_price=Decimal("88.00"),
            )
            # 经企业级治理审批后发布（此处直接调用领域发布逻辑）
            agg.publish(new_version=1)

        events = list(agg.pull_events())
        assert len(events) == 1
        event = events[0]
        assert isinstance(event, EnterpriseCustomizationPublishedEvent)
        assert event.tenant_id == tenant_id
        assert event.enterprise_product_id == enterprise_product_id
        assert event.version == 1

    async def test_publish_customization_version_must_increase(self) -> None:
        """定制发布版本号必须递增。"""
        tenant_id = uuid4()
        svc, _ = _new_customization_svc()

        with _apply_ctx(_make_ctx(tenant_id, permissions=frozenset({_ENTERPRISE_MANAGE}))):
            agg = await svc.create_customization(
                tenant_id=tenant_id,
                enterprise_product_id=uuid4(),
            )
            agg.publish(new_version=1)
            with pytest.raises(MDMError) as exc:
                agg.publish(new_version=1)
        assert exc.value.code == MDMErrorCode.SPEC_INSTANCE_INVALID


class TestEnterpriseReferenceFullFlowIntegration:
    """T16-06: 企业引用与定制全流程集成测试。"""

    async def test_full_flow_query_reference_customize_publish(self) -> None:
        """全流程：查询可引用集团商品→引用自动创建企业SKU→创建定制→发布事件。"""
        tenant_id = uuid4()
        gp_orm, gp_id = _make_group_product(code="GP-FLOW", name="集团商品全流程")
        group_skus = _make_group_skus(gp_id, count=2)

        ep_svc, _, esku_repo, ref_repo = _new_enterprise_product_svc(
            group_products={gp_id: gp_orm},
            group_skus={gp_id: group_skus},
        )
        ref_svc = _new_reference_svc(ref_repo)
        cust_svc, _ = _new_customization_svc()

        ctx = _make_ctx(tenant_id, permissions=frozenset({_ENTERPRISE_MANAGE}))

        with _apply_ctx(ctx):
            # 1. 查询可引用集团商品（集团商品已发布且未停用即可引用）
            available = await ep_svc._gp_repo.get_by_id(None, gp_id)
            assert available is not None
            assert available.published_version > 0
            assert available.status == GroupProductStatus.ACTIVE.value

            # 2. 引用集团商品，自动创建企业商品与企业 SKU
            ep_agg = await ep_svc.reference_group_product(
                tenant_id=tenant_id,
                group_product_id=gp_id,
                enterprise_product_code="EP-FLOW-001",
            )
            assert len(esku_repo.saved) == 2

            # 3. 查询引用关系（企业视角）
            my_refs = await ref_svc.list_references_by_tenant(tenant_id)
            assert len(my_refs) == 1
            assert my_refs[0].group_product_id == gp_id

            # 4. 创建企业定制
            cust_agg = await cust_svc.create_customization(
                tenant_id=tenant_id,
                enterprise_product_id=ep_agg.id.value,
                sales_price=Decimal("128.00"),
                inventory_strategy=InventoryStrategy.WARNING,
                safety_stock=Decimal("20"),
                cost_model=CostModelType.WEIGHTED_AVERAGE,
            )

            # 5. 审批发布定制，发布 EnterpriseCustomizationPublishedEvent
            cust_agg.publish(new_version=1)

        events = list(cust_agg.pull_events())
        assert len(events) == 1
        assert isinstance(events[0], EnterpriseCustomizationPublishedEvent)
        assert events[0].enterprise_product_id == ep_agg.id.value
        assert cust_agg.sales_price == Decimal("128.00")
        assert cust_agg.inventory_strategy == InventoryStrategy.WARNING


class TestEnterpriseProductAggregateCoverageIntegration:
    """T16-06: 企业商品聚合根行为覆盖测试（引用状态机与 SKU 管理）。"""

    def _make_ep(
        self, tenant_id: UUID | None = None, group_product_id: UUID | None = None
    ) -> EnterpriseProductAggregate:
        return EnterpriseProductAggregate(
            id=EntityId.generate(),
            tenant_id=tenant_id or uuid4(),
            group_product_id=group_product_id or uuid4(),
            enterprise_product_code="EP-COV",
            enterprise_product_name="覆盖商品",
        )

    def _make_esku(
        self, ep: EnterpriseProductAggregate, code: str = "ES-COV"
    ) -> EnterpriseSku:
        return EnterpriseSku(
            enterprise_sku_id=EntityId.generate(),
            tenant_id=ep.tenant_id,
            enterprise_product_id=ep.id,
            group_sku_id=uuid4(),
            enterprise_sku_code=code,
            enterprise_sku_name="企业SKU",
        )

    def test_mark_source_disabled(self) -> None:
        """集团商品停用时企业商品引用状态变为 source_disabled。"""
        ep = self._make_ep()
        ep.mark_source_disabled()
        assert ep.reference_status == ReferenceStatus.SOURCE_DISABLED
        assert ep.is_active() is False
        # 幂等
        ep.mark_source_disabled()
        assert ep.reference_status == ReferenceStatus.SOURCE_DISABLED

    def test_disable_transitions_to_released(self) -> None:
        """disable 将 active 转为 reference_released。"""
        ep = self._make_ep()
        ep.disable()
        assert ep.reference_status == ReferenceStatus.REFERENCE_RELEASED

    def test_disable_with_active_documents_rejected(self) -> None:
        """存在进行中单据时停用被拒绝。"""
        ep = self._make_ep()
        ep.mark_has_active_documents()
        with pytest.raises(MDMError) as exc:
            ep.disable()
        assert exc.value.code == MDMErrorCode.REFERENCE_HAS_ACTIVE_DOCUMENT

    def test_resolve_product_name_inherits_when_empty(self) -> None:
        """企业商品名称为空时继承集团商品名称。"""
        ep = EnterpriseProductAggregate(
            id=EntityId.generate(),
            tenant_id=uuid4(),
            group_product_id=uuid4(),
            enterprise_product_code="EP-N",
        )
        assert ep.resolve_product_name("集团名") == "集团名"
        ep.update_name("企业名")
        assert ep.resolve_product_name("集团名") == "企业名"

    def test_add_enterprise_sku_appends(self) -> None:
        """添加企业 SKU。"""
        ep = self._make_ep()
        sku = self._make_esku(ep, "ES-A")
        ep.add_enterprise_sku(sku)
        assert len(ep.enterprise_skus) == 1
        assert ep.get_enterprise_sku(sku.enterprise_sku_id) is not None
        assert ep.get_enterprise_sku(EntityId.generate()) is None

    def test_add_enterprise_sku_cross_tenant_rejected(self) -> None:
        """企业 SKU 跨租户被拒绝。"""
        ep = self._make_ep()
        sku = EnterpriseSku(
            enterprise_sku_id=EntityId.generate(),
            tenant_id=uuid4(),
            enterprise_product_id=ep.id,
            group_sku_id=uuid4(),
            enterprise_sku_code="ES-X",
        )
        with pytest.raises(MDMError) as exc:
            ep.add_enterprise_sku(sku)
        assert exc.value.code == MDMErrorCode.CROSS_TENANT_POLICY_DENIED

    def test_add_enterprise_sku_mismatched_product_rejected(self) -> None:
        """企业 SKU 所属商品不一致被拒绝。"""
        ep = self._make_ep()
        sku = EnterpriseSku(
            enterprise_sku_id=EntityId.generate(),
            tenant_id=ep.tenant_id,
            enterprise_product_id=EntityId.generate(),
            group_sku_id=uuid4(),
            enterprise_sku_code="ES-Y",
        )
        with pytest.raises(MDMError) as exc:
            ep.add_enterprise_sku(sku)
        assert exc.value.code == MDMErrorCode.SPEC_INSTANCE_INVALID

    def test_update_category(self) -> None:
        """更新企业分类。"""
        ep = self._make_ep()
        new_cat = uuid4()
        ep.update_category(new_cat)
        assert ep.enterprise_category_id == new_cat
        ep.update_category(None)
        assert ep.enterprise_category_id is None


class TestProductCustomizationCoverageIntegration:
    """T16-06: 商品定制聚合根行为覆盖测试。"""

    def _make_cust(self) -> ProductCustomizationAggregate:
        return ProductCustomizationAggregate(
            id=EntityId.generate(),
            tenant_id=uuid4(),
            enterprise_product_id=uuid4(),
        )

    def test_update_sales_price(self) -> None:
        """更新销售价格。"""
        cust = self._make_cust()
        cust.update_sales_price(Decimal("99.99"))
        assert cust.sales_price == Decimal("99.99")

    def test_update_sales_price_negative_rejected(self) -> None:
        """销售价格为负被拒绝。"""
        cust = self._make_cust()
        with pytest.raises(MDMError) as exc:
            cust.update_sales_price(Decimal("-1"))
        assert exc.value.code == MDMErrorCode.SPEC_INSTANCE_INVALID

    def test_update_purchase_price(self) -> None:
        """更新采购价格。"""
        cust = self._make_cust()
        cust.update_purchase_price(Decimal("50.00"))
        assert cust.purchase_price == Decimal("50.00")

    def test_update_purchase_price_negative_rejected(self) -> None:
        """采购价格为负被拒绝。"""
        cust = self._make_cust()
        with pytest.raises(MDMError) as exc:
            cust.update_purchase_price(Decimal("-1"))
        assert exc.value.code == MDMErrorCode.SPEC_INSTANCE_INVALID

    def test_update_inventory_strategy(self) -> None:
        """更新库存策略。"""
        cust = self._make_cust()
        cust.update_inventory_strategy(InventoryStrategy.APPROVAL)
        assert cust.inventory_strategy == InventoryStrategy.APPROVAL

    def test_update_safety_stock(self) -> None:
        """更新安全库存。"""
        cust = self._make_cust()
        cust.update_safety_stock(Decimal("20"))
        assert cust.safety_stock == Decimal("20")

    def test_update_safety_stock_negative_rejected(self) -> None:
        """安全库存为负被拒绝。"""
        cust = self._make_cust()
        with pytest.raises(MDMError) as exc:
            cust.update_safety_stock(Decimal("-1"))
        assert exc.value.code == MDMErrorCode.SPEC_INSTANCE_INVALID

    def test_update_cost_model(self) -> None:
        """更新计价策略。"""
        cust = self._make_cust()
        cust.update_cost_model(CostModelType.FIFO)
        assert cust.cost_model == CostModelType.FIFO

    def test_update_custom_attributes(self) -> None:
        """更新自定义属性。"""
        cust = self._make_cust()
        cust.update_custom_attributes({"region": "华东"})
        assert cust.custom_attributes == {"region": "华东"}


class TestProductReferenceAggregateCoverageIntegration:
    """T16-06: 商品引用关系聚合根行为覆盖测试。"""

    def _make_ref(self) -> ProductReferenceAggregate:
        return ProductReferenceAggregate.create(
            tenant_id=uuid4(),
            group_product_id=uuid4(),
            enterprise_product_id=uuid4(),
            referenced_by=uuid4(),
        )

    def test_ref_properties(self) -> None:
        """引用关系属性访问。"""
        ref = self._make_ref()
        assert ref.reference_status == ReferenceStatus.ACTIVE
        assert ref.is_active() is True
        assert ref.released_by is None
        assert ref.released_at is None
        assert ref.referenced_at is not None

    def test_ref_release_transitions(self) -> None:
        """释放引用关系。"""
        ref = self._make_ref()
        released_by = uuid4()
        ref.release(released_by)
        assert ref.reference_status == ReferenceStatus.REFERENCE_RELEASED
        assert ref.released_by == released_by
        assert ref.released_at is not None
        # 幂等
        ref.release(uuid4())
        assert ref.reference_status == ReferenceStatus.REFERENCE_RELEASED

    def test_ref_mark_source_disabled(self) -> None:
        """引用关系标记 source_disabled。"""
        ref = self._make_ref()
        ref.mark_source_disabled()
        assert ref.reference_status == ReferenceStatus.SOURCE_DISABLED
        # 幂等
        ref.mark_source_disabled()
        assert ref.reference_status == ReferenceStatus.SOURCE_DISABLED

    def test_ref_validate_no_duplicate_allows_different(self) -> None:
        """不同租户/不同集团商品不冲突。"""
        tenant = uuid4()
        gp = uuid4()
        ProductReferenceAggregate.validate_no_duplicate(
            existing_refs=[(uuid4(), gp), (tenant, uuid4())],
            tenant_id=tenant,
            group_product_id=gp,
        )


class TestEnterpriseSkuCoverageIntegration:
    """T16-06: 企业 SKU 实体行为覆盖测试。"""

    def test_resolve_sku_code_inherits_when_empty(self) -> None:
        """企业 SKU 编码为空时继承集团 SKU 编码。"""
        sku = EnterpriseSku(
            enterprise_sku_id=EntityId.generate(),
            tenant_id=uuid4(),
            enterprise_product_id=EntityId.generate(),
            group_sku_id=uuid4(),
        )
        assert sku.resolve_sku_code("GS-CODE") == "GS-CODE"
        assert sku.resolve_sku_name("GS-NAME") == "GS-NAME"

    def test_resolve_sku_code_uses_own_when_present(self) -> None:
        """企业 SKU 编码非空时使用企业编码。"""
        sku = EnterpriseSku(
            enterprise_sku_id=EntityId.generate(),
            tenant_id=uuid4(),
            enterprise_product_id=EntityId.generate(),
            group_sku_id=uuid4(),
            enterprise_sku_code="ES-CODE",
            enterprise_sku_name="ES-NAME",
        )
        assert sku.resolve_sku_code("GS-CODE") == "ES-CODE"
        assert sku.resolve_sku_name("GS-NAME") == "ES-NAME"

    def test_add_barcode_appends_unique(self) -> None:
        """添加条码去重。"""
        sku = EnterpriseSku(
            enterprise_sku_id=EntityId.generate(),
            tenant_id=uuid4(),
            enterprise_product_id=EntityId.generate(),
            group_sku_id=uuid4(),
            enterprise_barcode_list=["BC-1"],
        )
        sku.add_barcode("BC-2")
        sku.add_barcode("BC-1")
        assert sku.enterprise_barcode_list == ["BC-1", "BC-2"]

    def test_state_machine_disable_enable(self) -> None:
        """企业 SKU 启停状态机。"""
        sku = EnterpriseSku(
            enterprise_sku_id=EntityId.generate(),
            tenant_id=uuid4(),
            enterprise_product_id=EntityId.generate(),
            group_sku_id=uuid4(),
        )
        assert sku.status == EnterpriseSkuStatus.ACTIVE
        assert sku.is_active() is True
        sku.disable()
        assert sku.is_active() is False
        sku.enable()
        assert sku.is_active() is True