# EITP Phase 1 Release Evidence Archive

> **Release Baseline**: `v1.0.0-phase1` (`4954bca @ main`)
> **Core Freeze Baseline**: `8b7de20`
> **Date**: 2026-09-05
> **Status**: FINAL PASS / CLOSED

---

## 1. Release Identity

| Item | Value |
|------|-------|
| Git Tag | `v1.0.0-phase1` |
| Commit | `4954bcab5aca87c511e6e748ec7b8535b75ace79` |
| Branch | `main` |
| Core Freeze | `8b7de20` |
| Total Commits Since Freeze | 3 (`f796340`, `8de8b2b`, `4954bca`) |
| Files Changed Since Freeze | 339 |
| Lines Added | +25,784 |
| Lines Removed | -2,500 |

---

## 2. Core Freeze Integrity Audit

### 2.1 Core Business Logic Modification

```
Core Business Logic Modification = 0
```

All 11 frozen milestones (MT-001 ~ FIN-001 prerequisite) core domain/application/infrastructure code remains unchanged.

### 2.2 Infrastructure / Router Assembly Extension

```
Router Assembly Extension = 6 lines (3 imports + 3 include_router)
```

File: `backend/app/interfaces/api/v1/router.py`

```diff
+from app.interfaces.api.v1.fin.routes import fin_routes
+from app.interfaces.api.v1.sec import sec_router
+from app.interfaces.api.v1.biz_ops import biz_ops_router

+api_router.include_router(sec_router)
+api_router.include_router(fin_routes)
+api_router.include_router(biz_ops_router)
```

Classification: **CORE-FREEZE-COMPATIBLE-ASSEMBLY-EXTENSION**

### 2.3 Database Existing Table Modification

```
Database Existing Table Modification = 0
```

### 2.4 New Tables (Incremental Only)

```
New Tables = biz_ops_* only (via Alembic 080-085)
```

Migration chain: `079 → 080 → 081 → 082 → 083 → 084 → 085`

| Migration | Tables Created |
|-----------|---------------|
| 080 | biz_ops_feature_switches |
| 081 | biz_ops_business_rules, biz_ops_business_rule_versions |
| 082 | biz_ops_approval_flows, biz_ops_approval_nodes, biz_ops_approval_records |
| 083 | biz_ops_pricing_strategies, biz_ops_pricing_strategy_versions |
| 084 | biz_ops_tax_configs, biz_ops_inventory_strategies, biz_ops_inventory_strategy_versions |
| 085 | biz_ops_operation_audits |

All new tables include `tenant_id` column with RLS policy (reusing MT-001 RLS framework).

---

## 3. API Inventory (396 Endpoints)

| Module | Endpoints | Status |
|--------|-----------|--------|
| AUTH | 5 | Online |
| PLATFORM | 10 | Online |
| PLT | 39 | Online |
| IAM | 4 | Online |
| TENANT | 4 | Online |
| MDM (Group) | 25 | Online |
| MDM (Tenant) | 18 | Online |
| INV | 5 | Online |
| SAL | 55 | Online |
| PUR | 50 | Online |
| WMS | 26 | Online |
| FIN | 41 | Online |
| BIZ-OPS | 44 | Online |
| SEC | 19 | Online |
| REL | 20 | Online |
| PROD | 16 | Online |
| **Total** | **396** | **All HTTP 200** |

OpenAPI spec: `GET /openapi.json` → HTTP 200, 396 paths

---

## 4. BIZ-OPS Module Completion

### 4.1 Milestone Summary

| Milestone | Title | Tests | Status |
|-----------|-------|-------|--------|
| BIZ-OPS-001 | Feature Switch + Orchestrator Skeleton | 13 | PASS |
| BIZ-OPS-002 | Business Rule + Rule Executor + Linkage | 7 | PASS |
| BIZ-OPS-003 | Approval Flow + 5 Routing Strategies | 6 | PASS |
| BIZ-OPS-004 | Pricing Strategy + Strategy Resolver + Engine | 17 | PASS |
| BIZ-OPS-005 | Tax Config + Inventory Strategy + Engines | 31 | PASS |
| BIZ-OPS-006 | Operation Audit + 4 Orchestrators + 17 APIs | 11 | PASS |
| **Total** | | **85** | **6/6 COMPLETE** |

### 4.2 Code Assets

| Layer | Files | Key Components |
|-------|-------|----------------|
| Domain | 22 | 7 aggregates, 5 value objects, 9 services, 15 enums, 7 domain events |
| Application | 10 | 4 orchestrators, 3 app services, approval timeout scheduler, feature switch guard |
| Infrastructure | 9 | 7 repositories, ORM models, audit writer |
| Interfaces | 12 | 3 route files (44 endpoints), 8 schema files |
| Migrations | 6 | Alembic 080-085 |
| Frontend | 5 | 4 pages, 1 API client |
| Tests | 14 | 74 unit + 5 E2E + 6 DFX |

### 4.3 SDD Documentation

| Document | Size | Location |
|----------|------|----------|
| spec.md | 81 KB | `.codeartsdoer/specs/biz_ops_psi/` |
| design.md | 85 KB | `.codeartsdoer/specs/biz_ops_psi/` |
| tasks.md | 46 KB | `.codeartsdoer/specs/biz_ops_psi/` |

---

## 5. Bug Fixes

| # | Issue | Root Cause | Fix | Verification |
|---|-------|-----------|-----|-------------|
| 1 | `GET /openapi.json` → HTTP 500 | `MigrateRequest.examples` passed string instead of list | `placement.py:25`: `examples=[...]` | OpenAPI 200, 396 paths |
| 2 | Spec templates 404 | `enterprise_router` nested inside `router` (prefix `/group/spec-templates`), path became `/group/spec-templates/tenant/mdm/spec-templates` | Removed `router.include_router(enterprise_router)` from 4 route files, registered in `mdm/__init__.py` independently | 6/6 endpoints HTTP 200 |
| 3 | Attribute templates 404 | Same nesting issue | Same fix | Verified |
| 4 | Governance requests 404 | Same nesting issue | Same fix | Verified |
| 5 | Version management 404 | Same nesting issue | Same fix | Verified |

---

## 6. Deployment Verification

| Check | Result |
|-------|--------|
| Server | 192.168.1.70 (Debian, Python 3.13.5, Node v20) |
| Backend Process | uvicorn 0.0.0.0:8000 — running |
| Frontend | nginx — HTTP 200 |
| Login | JWT token issued successfully |
| Alembic | 080-085 all success |
| Frontend Build | `npx vite build` — PASS (6.36s) |
| MDM Group Endpoints | 3/3 HTTP 200 |
| MDM Tenant Endpoints | 3/3 HTTP 200 |
| BIZ-OPS Endpoints | 6/6 HTTP 200 |
| Known 404 | 0 |

---

## 7. Platform Architecture

```
                    EITP Platform
                         │
        ┌────────────────┼────────────────┐
        │                │                │
       IAM              MDM            BIZ-OPS
        │                │                │
        └────────────┬───┴───────┬────────┘
                     │           │
                    INV         WMS
                     │           │
              ┌──────┴──────┐    │
             PUR            SAL   │
              │              │    │
              └──────┬───────┘    │
                     │            │
                    FIN ◄─────────┘
                     │
             Settlement / Funds

    Cross-cutting: SEC · PLT · PROD · REL · PLATFORM · TENANT
```

---

## 8. Release Maintenance Policy

Phase 1 enters **Release Maintenance / Engineering Baseline** state.

### Allowed:
- Bug Fix
- Security Fix
- Data Integrity Fix
- Deployment Fix
- Compatibility Fix
- Performance Fix

### Not Allowed:
- Core domain model changes (frozen milestones)
- New features without Phase 2 SDD boundary

---

## 9. Audit Trail

```
Core Freeze (8b7de20)
    │
    ├── f796340  feat(EITP-FIN-001): Finance & Settlement Core
    ├── 8de8b2b  fix: resolve 404 errors across modules
    └── 4954bca  feat(EITP-BIZ-OPS): Phase 1 FINISH
         │
         └── v1.0.0-phase1  (RELEASE BASELINE)
```

---

## 10. Sign-off

| Role | Status | Date |
|------|--------|------|
| Engineering | FINAL PASS | 2026-09-05 |
| Project Management | CLOSED | 2026-09-05 |
| Release Baseline | `v1.0.0-phase1` | 2026-09-05 |

**EITP Engineering Phase 1 — COMPLETE / RELEASE BASELINE**