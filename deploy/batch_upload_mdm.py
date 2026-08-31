"""批量上传 MDM 相关文件到服务器。"""
import subprocess
import sys
from pathlib import Path

FILES = [
    # governance 领域层
    "backend/app/domain/governance/__init__.py",
    "backend/app/domain/governance/aggregates/__init__.py",
    "backend/app/domain/governance/aggregates/governance_workflow_aggregate.py",
    "backend/app/domain/governance/aggregates/master_data_version_aggregate.py",
    "backend/app/domain/governance/aggregates/negative_inventory_policy_audit_aggregate.py",
    "backend/app/domain/governance/entities/__init__.py",
    "backend/app/domain/governance/events/__init__.py",
    "backend/app/domain/governance/events/governance_events.py",
    "backend/app/domain/governance/repositories/__init__.py",
    "backend/app/domain/governance/services/__init__.py",
    "backend/app/domain/governance/services/governance_permission_checker.py",
    "backend/app/domain/governance/value_objects/__init__.py",
    "backend/app/domain/governance/value_objects/governance_state.py",
    # group_catalog 领域层
    "backend/app/domain/group_catalog/__init__.py",
    "backend/app/domain/group_catalog/aggregates/__init__.py",
    "backend/app/domain/group_catalog/aggregates/group_product_aggregate.py",
    "backend/app/domain/group_catalog/aggregates/group_category_aggregate.py",
    "backend/app/domain/group_catalog/aggregates/spec_template_aggregate.py",
    "backend/app/domain/group_catalog/aggregates/attribute_template_aggregate.py",
    "backend/app/domain/group_catalog/entities/__init__.py",
    "backend/app/domain/group_catalog/entities/group_sku.py",
    "backend/app/domain/group_catalog/entities/group_brand.py",
    "backend/app/domain/group_catalog/entities/group_unit.py",
    "backend/app/domain/group_catalog/events/__init__.py",
    "backend/app/domain/group_catalog/events/group_catalog_events.py",
    "backend/app/domain/group_catalog/repositories/__init__.py",
    "backend/app/domain/group_catalog/services/__init__.py",
    "backend/app/domain/group_catalog/services/group_catalog_permission_checker.py",
    "backend/app/domain/group_catalog/value_objects/__init__.py",
    "backend/app/domain/group_catalog/value_objects/group_unit_conversion.py",
    # enterprise_product 领域层
    "backend/app/domain/enterprise_product/__init__.py",
    "backend/app/domain/enterprise_product/aggregates/__init__.py",
    "backend/app/domain/enterprise_product/aggregates/enterprise_product_aggregate.py",
    "backend/app/domain/enterprise_product/aggregates/product_reference_aggregate.py",
    "backend/app/domain/enterprise_product/aggregates/product_customization_aggregate.py",
    "backend/app/domain/enterprise_product/aggregates/enterprise_category_aggregate.py",
    "backend/app/domain/enterprise_product/entities/__init__.py",
    "backend/app/domain/enterprise_product/entities/enterprise_sku.py",
    "backend/app/domain/enterprise_product/events/__init__.py",
    "backend/app/domain/enterprise_product/events/enterprise_product_events.py",
    "backend/app/domain/enterprise_product/repositories/__init__.py",
    "backend/app/domain/enterprise_product/services/__init__.py",
    "backend/app/domain/enterprise_product/services/cross_enterprise_ref_checker.py",
    # infrastructure
    "backend/app/infrastructure/mdm/__init__.py",
    "backend/app/infrastructure/mdm/models.py",
    "backend/app/infrastructure/governance/__init__.py",
    "backend/app/infrastructure/governance/governance_repositories.py",
    "backend/app/infrastructure/group_catalog/__init__.py",
    "backend/app/infrastructure/group_catalog/group_product_repository.py",
    "backend/app/infrastructure/enterprise_product/__init__.py",
    "backend/app/infrastructure/enterprise_product/enterprise_product_repository.py",
    "backend/app/infrastructure/master_data_query/__init__.py",
    "backend/app/infrastructure/master_data_query/master_data_query_redis_store.py",
    # audit
    "backend/app/domain/audit/__init__.py",
    "backend/app/domain/audit/audit_entry.py",
    "backend/app/domain/audit/master_data_audit_aggregate.py",
    # application group_catalog
    "backend/app/application/group_catalog/__init__.py",
    "backend/app/application/group_catalog/group_product_app_svc.py",
    "backend/app/application/group_catalog/spec_template_app_svc.py",
    "backend/app/application/group_catalog/attribute_template_app_svc.py",
    "backend/app/application/group_catalog/specification_instance_validator.py",
    "backend/app/application/group_catalog/attribute_instance_validator.py",
    # application enterprise_product
    "backend/app/application/enterprise_product/__init__.py",
    "backend/app/application/enterprise_product/enterprise_product_app_svc.py",
    "backend/app/application/enterprise_product/product_reference_app_svc.py",
    "backend/app/application/enterprise_product/enterprise_customization_app_svc.py",
]

missing = []
for f in FILES:
    if not Path(f).exists():
        missing.append(f)

if missing:
    print("Missing files:")
    for m in missing:
        print(f"  {m}")
    sys.exit(1)

for f in FILES:
    remote = f"/home/debian/EITP/{f.replace('/', '/')}"
    result = subprocess.run(
        [sys.executable, "deploy/ssh_upload.py", f, remote],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"FAILED: {f}")
        print(result.stderr)
    else:
        print(f"  uploaded: {f}")

print("Batch upload complete")