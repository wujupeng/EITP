"""批量上传 T12 接口层文件到服务器。"""
import subprocess
import sys
from pathlib import Path

FILES = [
    # Schema
    "backend/app/interfaces/schemas/mdm/__init__.py",
    "backend/app/interfaces/schemas/mdm/schemas.py",
    # MDM 路由
    "backend/app/interfaces/api/v1/mdm/__init__.py",
    "backend/app/interfaces/api/v1/mdm/group_product_routes.py",
    "backend/app/interfaces/api/v1/mdm/group_category_brand_routes.py",
    "backend/app/interfaces/api/v1/mdm/group_unit_routes.py",
    "backend/app/interfaces/api/v1/mdm/spec_template_routes.py",
    "backend/app/interfaces/api/v1/mdm/attribute_template_routes.py",
    "backend/app/interfaces/api/v1/mdm/enterprise_product_routes.py",
    "backend/app/interfaces/api/v1/mdm/product_reference_routes.py",
    "backend/app/interfaces/api/v1/mdm/enterprise_customization_routes.py",
    "backend/app/interfaces/api/v1/mdm/governance_workflow_routes.py",
    "backend/app/interfaces/api/v1/mdm/version_management_routes.py",
    "backend/app/interfaces/api/v1/mdm/negative_policy_routes.py",
    "backend/app/interfaces/api/v1/mdm/master_data_query_routes.py",
    "backend/app/interfaces/api/v1/mdm/master_data_audit_routes.py",
    # E2E 路由
    "backend/app/interfaces/api/v1/e2e_routes.py",
    # permission_interceptor
    "backend/app/interfaces/middleware/permission_interceptor.py",
]

missing = [f for f in FILES if not Path(f).exists()]
if missing:
    print("Missing files:")
    for m in missing:
        print(f"  {m}")
    sys.exit(1)

for f in FILES:
    remote = f"/home/debian/EITP/{f}"
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