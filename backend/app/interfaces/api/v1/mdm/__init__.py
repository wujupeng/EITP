"""MDM 路由聚合 - 挂载主数据中心各子模块路由。

集团级路由前缀：/api/v1/group/*（无 tenant_id，平台共享）
企业级路由前缀：/api/v1/tenant/mdm/*（含 tenant_id，租户隔离）
"""

from __future__ import annotations

from fastapi import APIRouter

from app.interfaces.api.v1.mdm.group_product_routes import router as group_product_router
from app.interfaces.api.v1.mdm.group_category_brand_routes import router as group_category_brand_router
from app.interfaces.api.v1.mdm.group_unit_routes import router as group_unit_router
from app.interfaces.api.v1.mdm.spec_template_routes import router as spec_template_router
from app.interfaces.api.v1.mdm.spec_template_routes import enterprise_router as spec_template_enterprise_router
from app.interfaces.api.v1.mdm.attribute_template_routes import router as attribute_template_router
from app.interfaces.api.v1.mdm.attribute_template_routes import enterprise_router as attribute_template_enterprise_router
from app.interfaces.api.v1.mdm.enterprise_product_routes import router as enterprise_product_router
from app.interfaces.api.v1.mdm.product_reference_routes import router as product_reference_router
from app.interfaces.api.v1.mdm.enterprise_customization_routes import router as enterprise_customization_router
from app.interfaces.api.v1.mdm.governance_workflow_routes import router as governance_workflow_router
from app.interfaces.api.v1.mdm.governance_workflow_routes import enterprise_router as governance_enterprise_router
from app.interfaces.api.v1.mdm.version_management_routes import router as version_management_router
from app.interfaces.api.v1.mdm.version_management_routes import enterprise_router as version_management_enterprise_router
from app.interfaces.api.v1.mdm.negative_policy_routes import router as negative_policy_router
from app.interfaces.api.v1.mdm.master_data_query_routes import router as master_data_query_router
from app.interfaces.api.v1.mdm.master_data_audit_routes import router as master_data_audit_router

mdm_router = APIRouter()
mdm_router.include_router(group_product_router)
mdm_router.include_router(group_category_brand_router)
mdm_router.include_router(group_unit_router)
mdm_router.include_router(spec_template_router)
mdm_router.include_router(spec_template_enterprise_router)
mdm_router.include_router(attribute_template_router)
mdm_router.include_router(attribute_template_enterprise_router)
mdm_router.include_router(enterprise_product_router)
mdm_router.include_router(product_reference_router)
mdm_router.include_router(enterprise_customization_router)
mdm_router.include_router(governance_workflow_router)
mdm_router.include_router(governance_enterprise_router)
mdm_router.include_router(version_management_router)
mdm_router.include_router(version_management_enterprise_router)
mdm_router.include_router(negative_policy_router)
mdm_router.include_router(master_data_query_router)
mdm_router.include_router(master_data_audit_router)
