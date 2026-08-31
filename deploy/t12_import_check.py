from app.interfaces.schemas.mdm import (
    CreateGroupProductRequest,
    GroupProductResponse,
    CreateGroupSkuRequest,
    GroupSkuResponse,
    CreateSpecTemplateRequest,
    SpecTemplateResponse,
    CreateAttributeTemplateRequest,
    AttributeTemplateResponse,
    ReferenceGroupProductRequest,
    EnterpriseProductResponse,
    CreateCustomizationRequest,
    CustomizationResponse,
    CreateGovernanceRequest,
    GovernanceRequestResponse,
    VersionCompareRequest,
    VersionCompareResponse,
    NegativePolicyConfigRequest,
    NegativePolicyConfigResponse,
    MasterDataQueryRequest,
    MasterDataQueryResponse,
    BarcodeLocateResponse,
    MasterDataAuditResponse,
)
print("T12-09 Schema imports: OK")

from app.interfaces.api.v1.mdm.group_product_routes import router as r1
from app.interfaces.api.v1.mdm.group_category_brand_routes import router as r2
from app.interfaces.api.v1.mdm.group_unit_routes import router as r3
from app.interfaces.api.v1.mdm.spec_template_routes import router as r4
from app.interfaces.api.v1.mdm.attribute_template_routes import router as r5
from app.interfaces.api.v1.mdm.enterprise_product_routes import router as r6
from app.interfaces.api.v1.mdm.product_reference_routes import router as r7
from app.interfaces.api.v1.mdm.enterprise_customization_routes import router as r8
from app.interfaces.api.v1.mdm.governance_workflow_routes import router as r9
from app.interfaces.api.v1.mdm.version_management_routes import router as r10
from app.interfaces.api.v1.mdm.negative_policy_routes import router as r11
from app.interfaces.api.v1.mdm.master_data_query_routes import router as r12
from app.interfaces.api.v1.mdm.master_data_audit_routes import router as r13
print("T12-01~08 Route imports: OK")

from app.interfaces.api.v1.mdm import mdm_router
print("T12 mdm_router aggregation: OK")

from app.interfaces.api.v1.e2e_routes import router as e2e_router
print("T12-08 E2E routes: OK")

print("All T12 imports successful")