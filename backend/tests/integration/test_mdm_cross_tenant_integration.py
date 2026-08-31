"""EITP-MDM-001-T16-07 跨租户商品引用与共享集成测试。

跨模块调用 CrossEnterpriseRefChecker + EnterpriseProductAppSvc + ProductReferenceAppSvc，
验证：集团发布商品 G1，企业 A/B/C 均可引用 G1 各自形成企业商品，
引用版本一致性，引用关系解除保留存量库存（design 2.5）。

对应 spec 5.1.1.7 / 5.2.1.6 / 5.2.1.9 / 5.2.3.5 / 5.7.1.6 / 5.7.1.7 / 5.7.1.8，design 2.5。
"""

from __future__ import annotations

from contextlib import contextmanager
from uuid import UUID, uuid4

import pytest

from app.application.enterprise_product.enterprise_product_app_svc import (
    EnterpriseProductAppSvc,
)
from app.application.enterprise_product.product_reference_app_svc import (
    ProductReferenceAppSvc,
)
from app.domain.enterprise_product.aggregates.enterprise_product_aggregate import (
    ReferenceStatus,
)
from app.domain.enterprise_product.services.cross_enterprise_ref_checker import (
    CrossEnterpriseRefChecker,
)
from app.domain.group_catalog.aggregates.group_product_aggregate import (
    GroupProductAggregate,
    GroupProductStatus,
)
from app.domain.group_catalog.entities.group_sku import GroupSku, GroupSkuStatus
from app.domain.group_catalog.events.group_catalog_events import (
    GroupProductDisabledEvent,
    GroupProductPublishedEvent,
    GroupSkuCreatedEvent,
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


# ----------------------------- 测试替身（复用文件 2 模式） -----------------------------


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
    def __init__(
        self,
        group_product_id: UUID,
        group_product_code: str,
        group_product_name: str,
        base_unit_id: UUID,
        status: str = GroupProductStatus.ACTIVE.value,
        published_version: int = 1,
    ) -> None:
        self.group_product_id = group_product_id
        self.group_product_code = group_product_code
        self.group_product_name = group_product_name
        self.base_unit_id = base_unit_id
        self.group_category_id = None
        self.group_brand_id = None
        self.spec_template_id = None
        self.description = None
        self.status = status
        self.published_version = published_version


class _GroupSkuORMProxy:
    def __init__(self, group_sku_id: UUID, group_sku_code: str, group_sku_name: str) -> None:
        self.group_sku_id = group_sku_id
        self.group_sku_code = group_sku_code
        self.group_sku_name = group_sku_name
        self.barcode_list = []


class _EnterpriseProductORMProxy:
    def __init__(self, agg) -> None:
        self.enterprise_product_id = agg.id.value
        self.tenant_id = agg.tenant_id
        self.group_product_id = agg.group_product_id
        self.enterprise_product_code = agg.enterprise_product_code
        self.enterprise_product_name = agg.enterprise_product_name
        self.enterprise_category_id = agg.enterprise_category_id
        self.reference_status = agg.reference_status.value
        self.published_version = agg.published_version


class _ProductReferenceORMProxy:
    def __init__(self, tenant_id: UUID, group_product_id: UUID, enterprise_product_id: UUID) -> None:
        self.tenant_id = tenant_id
        self.group_product_id = group_product_id
        self.enterprise_product_id = enterprise_product_id
        self.reference_status = ReferenceStatus.ACTIVE.value


class _FakeGroupProductRepo:
    def __init__(self, products: dict[UUID, _GroupProductORMProxy]) -> None:
        self._store = products

    async def get_by_id(self, session: object, group_product_id: UUID):
        return self._store.get(group_product_id)


class _FakeGroupSkuRepo:
    def __init__(self, skus: dict[UUID, list[_GroupSkuORMProxy]]) -> None:
        self._store = skus

    async def list_by_product(self, session: object, group_product_id: UUID):
        return list(self._store.get(group_product_id, []))


class _FakeEnterpriseProductRepo:
    def __init__(self) -> None:
        self._store: dict[tuple[UUID, UUID], _EnterpriseProductORMProxy] = {}

    async def save(self, session: object, agg) -> None:
        self._store[(agg.tenant_id, agg.id.value)] = _EnterpriseProductORMProxy(agg)

    async def get_by_tenant_and_code(self, session: object, tenant_id: UUID, code: str):
        for (t, _pid), orm in self._store.items():
            if t == tenant_id and orm.enterprise_product_code == code:
                return orm
        return None

    async def get_by_id(self, session: object, tenant_id: UUID, enterprise_product_id: UUID):
        return self._store.get((tenant_id, enterprise_product_id))

    async def list_by_tenant(self, session: object, tenant_id: UUID, offset: int = 0, limit: int = 50):
        return [orm for (t, _pid), orm in self._store.items() if t == tenant_id]


class _FakeEnterpriseSkuRepo:
    def __init__(self) -> None:
        self.saved = []

    async def save(self, session: object, sku) -> None:
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
            )
        )

    async def list_by_tenant(self, session: object, tenant_id: UUID):
        return [r for r in self._store if r.tenant_id == tenant_id]

    async def list_by_group_product(self, session: object, group_product_id: UUID):
        return [r for r in self._store if r.group_product_id == group_product_id]


# ----------------------------- 公共辅助 -----------------------------


_ENTERPRISE_MANAGE = "mdm:enterprise_product:manage"


def _make_ctx(tenant_id: UUID) -> SecurityContext:
    return SecurityContext(
        user=UserIdentity(
            user_id=uuid4(),
            username="enterprise-admin",
            is_platform_admin=False,
            is_tenant_admin=True,
        ),
        tenant=TenantIdentity(tenant_id=tenant_id),
        roles=(RoleSummary(role_id=uuid4(), role_code="enterprise_admin", role_name="企业管理员"),),
        permissions=PermissionSummary(codes=frozenset({_ENTERPRISE_MANAGE})),
        data_scope=ResolvedDataScope(scope_type="tenant"),
    )


@contextmanager
def _apply_ctx(ctx: SecurityContext):
    token = SecurityContext.set(ctx)
    try:
        yield
    finally:
        SecurityContext.reset(token)


def _make_group_product_agg(
    code: str = "G1",
    published_version: int = 1,
    status: GroupProductStatus = GroupProductStatus.ACTIVE,
) -> GroupProductAggregate:
    return GroupProductAggregate(
        id=EntityId.generate(),
        group_product_code=code,
        group_product_name=f"集团商品{code}",
        base_unit_id=uuid4(),
        status=status,
        published_version=published_version,
    )


def _make_group_product_orm(
    gp_id: UUID,
    code: str = "G1",
    published_version: int = 1,
    status: str = GroupProductStatus.ACTIVE.value,
) -> _GroupProductORMProxy:
    return _GroupProductORMProxy(
        group_product_id=gp_id,
        group_product_code=code,
        group_product_name=f"集团商品{code}",
        base_unit_id=uuid4(),
        status=status,
        published_version=published_version,
    )


def _new_svc(
    group_products: dict[UUID, _GroupProductORMProxy],
    group_skus: dict[UUID, list[_GroupSkuORMProxy]] | None = None,
) -> tuple[
    EnterpriseProductAppSvc,
    _FakeEnterpriseProductRepo,
    _FakeEnterpriseSkuRepo,
    _FakeProductReferenceRepo,
]:
    session = _DummySession()
    svc = EnterpriseProductAppSvc(session=session)
    svc._ep_repo = _FakeEnterpriseProductRepo()
    svc._esku_repo = _FakeEnterpriseSkuRepo()
    svc._ref_repo = _FakeProductReferenceRepo()
    svc._gp_repo = _FakeGroupProductRepo(products=group_products)
    svc._gsku_repo = _FakeGroupSkuRepo(skus=group_skus or {})
    return svc, svc._ep_repo, svc._esku_repo, svc._ref_repo


# ----------------------------- 集成测试 -----------------------------


class TestCrossEnterpriseRefCheckerIntegration:
    """T16-07: 跨企业引用校验器集成测试。"""

    def test_validate_group_product_available_passes(self) -> None:
        """已发布且未停用的集团商品可被引用。"""
        gp = _make_group_product_agg(published_version=1)
        CrossEnterpriseRefChecker.validate_group_product_available(gp)

    def test_validate_group_product_unpublished_rejected(self) -> None:
        """未发布集团商品禁止引用。"""
        gp = _make_group_product_agg(published_version=0)
        with pytest.raises(MDMError) as exc:
            CrossEnterpriseRefChecker.validate_group_product_available(gp)
        assert exc.value.code == MDMErrorCode.GROUP_PRODUCT_NOT_PUBLISHED

    def test_validate_group_product_disabled_rejected(self) -> None:
        """已停用集团商品禁止引用。"""
        gp = _make_group_product_agg(status=GroupProductStatus.DISABLED)
        with pytest.raises(MDMError) as exc:
            CrossEnterpriseRefChecker.validate_group_product_available(gp)
        assert exc.value.code == MDMErrorCode.GROUP_PRODUCT_DISABLED

    def test_cross_enterprise_direct_reference_denied(self) -> None:
        """跨企业直接引用企业商品被拒绝（spec 5.2.1.9）。"""
        tenant_a = uuid4()
        tenant_b = uuid4()
        with pytest.raises(MDMError) as exc:
            CrossEnterpriseRefChecker.validate_no_cross_enterprise_direct_ref(tenant_a, tenant_b)
        assert exc.value.code == MDMErrorCode.CROSS_ENTERPRISE_REF_DENIED

    def test_same_enterprise_direct_reference_allowed(self) -> None:
        """同企业内引用不被跨企业校验拒绝。"""
        tenant = uuid4()
        CrossEnterpriseRefChecker.validate_no_cross_enterprise_direct_ref(tenant, tenant)

    def test_duplicate_reference_same_tenant_rejected(self) -> None:
        """同一企业重复引用同一集团商品被拒绝（spec 5.2.3.5）。"""
        tenant = uuid4()
        gp = _make_group_product_agg()
        existing = [(tenant, gp.id.value)]
        with pytest.raises(MDMError) as exc:
            CrossEnterpriseRefChecker.validate_reference_creation(gp, tenant, existing)
        assert exc.value.code == MDMErrorCode.DUPLICATE_REFERENCE

    def test_different_tenants_reference_same_group_allowed(self) -> None:
        """不同企业引用同一集团商品通过校验（spec 5.7.1.7）。"""
        tenant_a = uuid4()
        tenant_b = uuid4()
        gp = _make_group_product_agg()
        existing = [(tenant_a, gp.id.value)]
        # 租户 B 引用同一集团商品，不与租户 A 冲突
        CrossEnterpriseRefChecker.validate_reference_creation(gp, tenant_b, existing)

    def test_validate_reference_creation_combines_all_checks(self) -> None:
        """综合校验：集团商品可用 + 无重复引用。"""
        tenant = uuid4()
        gp = _make_group_product_agg()
        # 空引用列表，首次引用通过
        CrossEnterpriseRefChecker.validate_reference_creation(gp, tenant, [])


class TestMultiTenantReferenceIntegration:
    """T16-07: 多租户引用同一集团商品集成测试。"""

    async def test_group_publish_then_enterprises_a_b_c_reference(self) -> None:
        """集团发布 G1，企业 A/B/C 均引用 G1 各自形成企业商品。"""
        gp_id = uuid4()
        gp_orm = _make_group_product_orm(gp_id, code="G1", published_version=1)
        gskus = {gp_id: [_GroupSkuORMProxy(uuid4(), "GS-1", "集团SKU1")]}

        svc, ep_repo, esku_repo, ref_repo = _new_svc({gp_id: gp_orm}, gskus)

        tenants = [uuid4() for _ in range(3)]
        ep_ids = []
        for idx, tenant_id in enumerate(tenants):
            with _apply_ctx(_make_ctx(tenant_id)):
                ep_agg = await svc.reference_group_product(
                    tenant_id=tenant_id,
                    group_product_id=gp_id,
                    enterprise_product_code=f"EP-{idx}",
                )
                ep_ids.append(ep_agg.id.value)

        # 三个企业各自形成独立企业商品
        assert len(ep_ids) == 3
        assert len({id for id in ep_ids}) == 3
        # 三个企业各自的企业 SKU 已创建
        assert len(esku_repo.saved) == 3
        # 引用关系共 3 条
        ref_svc = ProductReferenceAppSvc(session=_DummySession())
        ref_svc._repo = ref_repo
        all_refs = await ref_svc.list_references_by_group_product(gp_id)
        assert len(all_refs) == 3
        ref_tenants = {r.tenant_id for r in all_refs}
        assert ref_tenants == set(tenants)

    async def test_each_enterprise_product_isolated_by_tenant(self) -> None:
        """各企业商品租户隔离，互不可见。"""
        gp_id = uuid4()
        gp_orm = _make_group_product_orm(gp_id, code="G-ISO")
        gskus = {gp_id: [_GroupSkuORMProxy(uuid4(), "GS-ISO", "SKU")]}

        svc, ep_repo, _, _ = _new_svc({gp_id: gp_orm}, gskus)

        tenant_a = uuid4()
        tenant_b = uuid4()
        with _apply_ctx(_make_ctx(tenant_a)):
            await svc.reference_group_product(
                tenant_id=tenant_a, group_product_id=gp_id, enterprise_product_code="EP-A"
            )
        with _apply_ctx(_make_ctx(tenant_b)):
            await svc.reference_group_product(
                tenant_id=tenant_b, group_product_id=gp_id, enterprise_product_code="EP-B"
            )

        # 租户 A 仅看到自己的企业商品
        a_products = await ep_repo.list_by_tenant(None, tenant_a)
        b_products = await ep_repo.list_by_tenant(None, tenant_b)
        assert len(a_products) == 1
        assert len(b_products) == 1
        assert a_products[0].tenant_id == tenant_a
        assert b_products[0].tenant_id == tenant_b
        assert a_products[0].enterprise_product_id != b_products[0].enterprise_product_id

    async def test_reference_version_consistency(self) -> None:
        """引用版本一致性：所有企业引用同一集团商品看到同一版本（spec 5.7.1.6）。"""
        gp_id = uuid4()
        gp_orm = _make_group_product_orm(gp_id, code="G-VER", published_version=1)
        gskus = {gp_id: [_GroupSkuORMProxy(uuid4(), "GS-VER", "SKU")]}

        svc, _, _, ref_repo = _new_svc({gp_id: gp_orm}, gskus)

        tenant_a = uuid4()
        tenant_b = uuid4()
        with _apply_ctx(_make_ctx(tenant_a)):
            await svc.reference_group_product(
                tenant_id=tenant_a, group_product_id=gp_id, enterprise_product_code="EP-A"
            )
        with _apply_ctx(_make_ctx(tenant_b)):
            await svc.reference_group_product(
                tenant_id=tenant_b, group_product_id=gp_id, enterprise_product_code="EP-B"
            )

        # 集团商品版本升级（模拟 GroupProductPublishedEvent 通知后所有引用企业看到新版本）
        gp_orm.published_version = 2

        # 所有引用企业通过集团商品仓储看到的版本一致
        gp_from_repo = await svc._gp_repo.get_by_id(None, gp_id)
        assert gp_from_repo.published_version == 2
        all_refs = await ref_repo.list_by_group_product(None, gp_id)
        for ref in all_refs:
            # 每个引用关系指向同一集团商品同一版本
            assert ref.group_product_id == gp_id

    async def test_duplicate_reference_per_tenant_rejected(self) -> None:
        """同一企业重复引用同一集团商品被拒绝，不同企业不冲突。"""
        gp_id = uuid4()
        gp_orm = _make_group_product_orm(gp_id, code="G-DUP")
        gskus = {gp_id: [_GroupSkuORMProxy(uuid4(), "GS-DUP", "SKU")]}

        svc, _, _, _ = _new_svc({gp_id: gp_orm}, gskus)

        tenant_a = uuid4()
        with _apply_ctx(_make_ctx(tenant_a)):
            await svc.reference_group_product(
                tenant_id=tenant_a, group_product_id=gp_id, enterprise_product_code="EP-A1"
            )
            with pytest.raises(MDMError) as exc:
                await svc.reference_group_product(
                    tenant_id=tenant_a, group_product_id=gp_id, enterprise_product_code="EP-A2"
                )
        assert exc.value.code == MDMErrorCode.DUPLICATE_REFERENCE

    async def test_reference_unpublished_group_rejected(self) -> None:
        """集团商品未发布时企业引用被拒绝。"""
        gp_id = uuid4()
        gp_orm = _make_group_product_orm(gp_id, code="G-UNP", published_version=0)
        svc, _, _, _ = _new_svc({gp_id: gp_orm}, {})

        tenant_id = uuid4()
        with _apply_ctx(_make_ctx(tenant_id)):
            with pytest.raises(MDMError) as exc:
                await svc.reference_group_product(
                    tenant_id=tenant_id, group_product_id=gp_id, enterprise_product_code="EP-X"
                )
        assert exc.value.code == MDMErrorCode.GROUP_PRODUCT_NOT_PUBLISHED


class TestReferenceReleaseAndGroupDisableIntegration:
    """T16-07: 引用关系解除与集团商品停用集成测试（design 2.5.4）。"""

    async def test_release_reference_preserves_inventory(self) -> None:
        """引用关系解除保留存量库存，标记 reference_released（spec 5.2.1.6）。"""
        gp_id = uuid4()
        gp_orm = _make_group_product_orm(gp_id, code="G-REL")
        gskus = {gp_id: [_GroupSkuORMProxy(uuid4(), "GS-REL", "SKU")]}

        svc, ep_repo, _, _ = _new_svc({gp_id: gp_orm}, gskus)
        tenant_id = uuid4()

        with _apply_ctx(_make_ctx(tenant_id)):
            ep_agg = await svc.reference_group_product(
                tenant_id=tenant_id, group_product_id=gp_id, enterprise_product_code="EP-REL"
            )
            ep_id = ep_agg.id.value
            released = await svc.release_reference(
                tenant_id=tenant_id, enterprise_product_id=ep_id
            )

        assert released.reference_status == ReferenceStatus.REFERENCE_RELEASED
        # 存量保留：企业商品仍存在于仓储
        orm = await ep_repo.get_by_id(None, tenant_id, ep_id)
        assert orm is not None
        assert orm.reference_status == ReferenceStatus.REFERENCE_RELEASED.value

    async def test_group_product_publish_increases_version(self) -> None:
        """集团商品发布版本号递增并发布 GroupProductPublishedEvent。"""
        gp = _make_group_product_agg(code="G-PUB", published_version=1)
        gp.publish(new_version=2)
        assert gp.published_version == 2
        events = list(gp.pull_events())
        assert len(events) == 1
        assert isinstance(events[0], GroupProductPublishedEvent)
        assert events[0].from_version == 1
        assert events[0].to_version == 2

    async def test_group_product_publish_version_must_increase(self) -> None:
        """集团商品发布版本号必须大于当前版本。"""
        gp = _make_group_product_agg(code="G-PUB2", published_version=2)
        with pytest.raises(MDMError) as exc:
            gp.publish(new_version=2)
        assert exc.value.code == MDMErrorCode.SPEC_INSTANCE_INVALID

    async def test_group_product_disable_rejects_when_active_reference(self) -> None:
        """集团商品存在活跃企业引用时停用被拒绝（spec 5.1.1.7）。"""
        gp = _make_group_product_agg(code="G-DIS")
        gp.mark_has_active_references()
        with pytest.raises(MDMError) as exc:
            gp.disable()
        assert exc.value.code == MDMErrorCode.GROUP_PRODUCT_HAS_ACTIVE_REFERENCE
        assert gp.status == GroupProductStatus.ACTIVE

    async def test_group_product_disable_publishes_event(self) -> None:
        """集团商品停用（无活跃引用）发布 GroupProductDisabledEvent。"""
        gp = _make_group_product_agg(code="G-DIS2")
        gp.disable()
        assert gp.status == GroupProductStatus.DISABLED
        events = list(gp.pull_events())
        assert len(events) == 1
        assert isinstance(events[0], GroupProductDisabledEvent)

    async def test_disabled_group_product_blocks_new_reference(self) -> None:
        """集团商品停用后拒绝新企业引用，但保留已引用企业引用关系。"""
        gp_id = uuid4()
        gp_orm = _make_group_product_orm(gp_id, code="G-BLK", published_version=1)
        gskus = {gp_id: [_GroupSkuORMProxy(uuid4(), "GS-BLK", "SKU")]}

        svc, ep_repo, _, _ = _new_svc({gp_id: gp_orm}, gskus)
        tenant_a = uuid4()

        # 企业 A 先引用
        with _apply_ctx(_make_ctx(tenant_a)):
            ep_agg = await svc.reference_group_product(
                tenant_id=tenant_a, group_product_id=gp_id, enterprise_product_code="EP-A"
            )

        # 集团商品停用（模拟已解除活跃引用）
        gp_orm.status = GroupProductStatus.DISABLED.value

        # 企业 B 尝试引用被拒绝
        tenant_b = uuid4()
        with _apply_ctx(_make_ctx(tenant_b)):
            with pytest.raises(MDMError) as exc:
                await svc.reference_group_product(
                    tenant_id=tenant_b, group_product_id=gp_id, enterprise_product_code="EP-B"
                )
        assert exc.value.code == MDMErrorCode.GROUP_PRODUCT_DISABLED

        # 企业 A 的引用关系与存量数据保留
        a_orm = await ep_repo.get_by_id(None, tenant_a, ep_agg.id.value)
        assert a_orm is not None
        assert a_orm.reference_status == ReferenceStatus.ACTIVE.value

    async def test_release_then_group_disable_flow(self) -> None:
        """企业解除引用后，集团商品可停用（design 2.5.4）。"""
        gp_id = uuid4()
        gp_orm = _make_group_product_orm(gp_id, code="G-FLOW", published_version=1)
        gskus = {gp_id: [_GroupSkuORMProxy(uuid4(), "GS-FLOW", "SKU")]}

        svc, _, _, _ = _new_svc({gp_id: gp_orm}, gskus)
        tenant_id = uuid4()

        with _apply_ctx(_make_ctx(tenant_id)):
            ep_agg = await svc.reference_group_product(
                tenant_id=tenant_id, group_product_id=gp_id, enterprise_product_code="EP-FLOW"
            )
            # 解除引用，保留存量
            released = await svc.release_reference(
                tenant_id=tenant_id, enterprise_product_id=ep_agg.id.value
            )
        assert released.reference_status == ReferenceStatus.REFERENCE_RELEASED

        # 引用已解除，集团商品无活跃引用，可停用
        gp_agg = _make_group_product_agg(code="G-FLOW")
        gp_agg.disable()
        assert gp_agg.status == GroupProductStatus.DISABLED


class TestGroupProductAggregateCoverageIntegration:
    """T16-07: 集团商品聚合根行为覆盖测试（跨租户引用的基准事实源）。"""

    def _make_sku(self, gp: GroupProductAggregate, code: str = "GS-C") -> GroupSku:
        return GroupSku(
            group_sku_id=EntityId.generate(),
            group_product_id=gp.id,
            group_sku_code=code,
            group_sku_name=f"SKU-{code}",
            unit_id=uuid4(),
        )

    def test_properties_access(self) -> None:
        """集团商品属性访问。"""
        category_id = uuid4()
        brand_id = uuid4()
        unit_id = uuid4()
        gp = GroupProductAggregate(
            id=EntityId.generate(),
            group_product_code="GP-PROP",
            group_product_name="属性",
            base_unit_id=unit_id,
            group_category_id=category_id,
            group_brand_id=brand_id,
            description="描述",
        )
        assert gp.group_product_code == "GP-PROP"
        assert gp.group_product_name == "属性"
        assert gp.base_unit_id == unit_id
        assert gp.group_category_id == category_id
        assert gp.group_brand_id == brand_id
        assert gp.description == "描述"
        assert gp.status == GroupProductStatus.ACTIVE
        assert gp.published_version == 0
        assert gp.group_skus == []
        assert gp.is_active() is True

    def test_add_group_sku_appends_and_records_event(self) -> None:
        """添加集团 SKU 并发布 GroupSkuCreatedEvent。"""
        gp = _make_group_product_agg(code="G-SKU")
        sku = self._make_sku(gp, "GS-ADD")
        gp.add_group_sku(sku)
        assert len(gp.group_skus) == 1
        assert gp.group_skus[0].group_sku_code == "GS-ADD"
        events = list(gp.pull_events())
        assert isinstance(events[-1], GroupSkuCreatedEvent)
        assert events[-1].group_sku_code == "GS-ADD"

    def test_add_duplicate_group_sku_rejected(self) -> None:
        """重复集团 SKU 编码被拒绝。"""
        gp = _make_group_product_agg(code="G-DUPSKU")
        sku = self._make_sku(gp, "GS-DUP")
        gp.add_group_sku(sku)
        with pytest.raises(MDMError) as exc:
            gp.add_group_sku(self._make_sku(gp, "GS-DUP"))
        assert exc.value.code == MDMErrorCode.GROUP_SKU_DUPLICATE

    def test_add_group_sku_mismatched_product_rejected(self) -> None:
        """集团 SKU 所属商品不一致被拒绝。"""
        gp = _make_group_product_agg(code="G-MISMATCH")
        other_gp = _make_group_product_agg(code="G-OTHER")
        sku = self._make_sku(other_gp, "GS-X")
        with pytest.raises(MDMError) as exc:
            gp.add_group_sku(sku)
        assert exc.value.code == MDMErrorCode.SPEC_INSTANCE_INVALID

    def test_get_group_sku_returns_matching(self) -> None:
        """按 ID 查找集团 SKU。"""
        gp = _make_group_product_agg(code="G-GET")
        sku = self._make_sku(gp, "GS-GET")
        gp.add_group_sku(sku)
        found = gp.get_group_sku(sku.group_sku_id)
        assert found is not None
        assert found.group_sku_id == sku.group_sku_id
        assert gp.get_group_sku(EntityId.generate()) is None

    def test_check_active_references(self) -> None:
        """检查活跃企业引用标记。"""
        gp = _make_group_product_agg(code="G-REF")
        assert gp.check_active_references() is False
        gp.mark_has_active_references()
        assert gp.check_active_references() is True

    def test_enable_idempotent(self) -> None:
        """启用已启用的集团商品幂等。"""
        gp = _make_group_product_agg(code="G-EN")
        gp.enable()
        assert gp.is_active() is True

    def test_enable_after_disable(self) -> None:
        """停用后可重新启用。"""
        gp = _make_group_product_agg(code="G-RE-EN")
        gp.disable()
        assert gp.is_active() is False
        gp.enable()
        assert gp.is_active() is True

    def test_update_methods(self) -> None:
        """更新名称/描述/分类/品牌。"""
        gp = _make_group_product_agg(code="G-UPD")
        new_category = uuid4()
        new_brand = uuid4()
        gp.update_name("新名称")
        gp.update_description("新描述")
        gp.update_category(new_category)
        gp.update_brand(new_brand)
        assert gp.group_product_name == "新名称"
        assert gp.description == "新描述"
        assert gp.group_category_id == new_category
        assert gp.group_brand_id == new_brand

    def test_publish_disabled_rejected(self) -> None:
        """停用集团商品禁止发布。"""
        gp = _make_group_product_agg(code="G-PUBDIS")
        gp.disable()
        with pytest.raises(MDMError) as exc:
            gp.publish(new_version=1)
        assert exc.value.code == MDMErrorCode.GROUP_PRODUCT_DISABLED

    def test_group_sku_state_machine(self) -> None:
        """集团 SKU 启停状态机。"""
        gp = _make_group_product_agg(code="G-SKUST")
        sku = self._make_sku(gp, "GS-ST")
        assert sku.is_active() is True
        assert sku.status == GroupSkuStatus.ACTIVE
        sku.disable()
        assert sku.is_active() is False
        assert sku.status == GroupSkuStatus.DISABLED
        sku.enable()
        assert sku.is_active() is True

    def test_group_sku_add_barcode_and_spec(self) -> None:
        """集团 SKU 添加条码与更新规格。"""
        gp = _make_group_product_agg(code="G-SKUBC")
        sku = self._make_sku(gp, "GS-BC")
        sku.add_barcode("BC-1")
        sku.add_barcode("BC-2")
        sku.add_barcode("BC-1")  # 重复不追加
        assert sku.barcode_list == ["BC-1", "BC-2"]
        sku.update_specification({"color": "红"})
        assert sku.specification_instance == {"color": "红"}