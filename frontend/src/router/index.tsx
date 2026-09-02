import { createBrowserRouter, type RouteObject, Navigate } from 'react-router-dom'
import MainLayout from '@/layouts/MainLayout'
import Login from '@/pages/auth/Login'
import TenantManagement from '@/pages/platform/TenantManagement'
import PlacementManagement from '@/pages/platform/PlacementManagement'
import BackupManagement from '@/pages/platform/BackupManagement'
import HierarchyManagement from '@/pages/tenant/HierarchyManagement'
import GroupReport from '@/pages/group/GroupReport'
import Operations from '@/pages/business/Operations'
import MasterDataManagement from '@/pages/business/MasterDataManagement'
import UserManagement from '@/pages/iam/UserManagement'
import ProductManagement from '@/pages/inv/ProductManagement'
import InventoryQuery from '@/pages/inv/InventoryQuery'
import InventoryTransaction from '@/pages/inv/InventoryTransaction'
import GroupProductManagement from '@/pages/mdm/GroupProductManagement'
import GroupCategoryBrandPage from '@/pages/mdm/GroupCategoryBrandPage'
import SpecTemplateManagement from '@/pages/mdm/SpecTemplateManagement'
import AttributeTemplateManagement from '@/pages/mdm/AttributeTemplateManagement'
import EnterpriseProductManagement from '@/pages/mdm/EnterpriseProductManagement'
import EnterpriseCustomizationPage from '@/pages/mdm/EnterpriseCustomizationPage'
import GovernanceManagement from '@/pages/mdm/GovernanceManagement'
import VersionManagement from '@/pages/mdm/VersionManagement'
import NegativePolicyManagement from '@/pages/mdm/NegativePolicyManagement'
import MasterDataQuery from '@/pages/mdm/MasterDataQuery'
import MasterDataAudit from '@/pages/mdm/MasterDataAudit'
import WmsSpaceManagementPage from '@/pages/wms/WmsSpaceManagementPage'
import WmsInventoryPositionsPage from '@/pages/wms/WmsInventoryPositionsPage'
import WmsReceivingPage from '@/pages/wms/WmsReceivingPage'
import WmsPutawayPage from '@/pages/wms/WmsPutawayPage'
import WmsPickingPage from '@/pages/wms/WmsPickingPage'
import WmsTransferPage from '@/pages/wms/WmsTransferPage'
import WmsShippingPage from '@/pages/wms/WmsShippingPage'
import WmsTaskManagementPage from '@/pages/wms/WmsTaskManagementPage'
import WmsReconcilePage from '@/pages/wms/WmsReconcilePage'
import PurSupplierManagementPage from '@/pages/pur/PurSupplierManagementPage'
import PurQuotationManagementPage from '@/pages/pur/PurQuotationManagementPage'
import PurSupplierEvaluationPage from '@/pages/pur/PurSupplierEvaluationPage'
import PurRequestManagementPage from '@/pages/pur/PurRequestManagementPage'
import PurOrderManagementPage from '@/pages/pur/PurOrderManagementPage'
import PurOrderDetailPage from '@/pages/pur/PurOrderDetailPage'
import PurReceiptManagementPage from '@/pages/pur/PurReceiptManagementPage'
import PurReturnManagementPage from '@/pages/pur/PurReturnManagementPage'
import PurSettlementManagementPage from '@/pages/pur/PurSettlementManagementPage'
import PurInvoiceManagementPage from '@/pages/pur/PurInvoiceManagementPage'
import PurPaymentManagementPage from '@/pages/pur/PurPaymentManagementPage'
import PurReconcileManagementPage from '@/pages/pur/PurReconcileManagementPage'
import SalCustomerManagementPage from '@/pages/sal/SalCustomerManagementPage'
import SalCustomerCategoryPage from '@/pages/sal/SalCustomerCategoryPage'
import SalCreditLimitPage from '@/pages/sal/SalCreditLimitPage'
import SalCustomerPricingPage from '@/pages/sal/SalCustomerPricingPage'
import SalQuotationManagementPage from '@/pages/sal/SalQuotationManagementPage'
import SalOrderManagementPage from '@/pages/sal/SalOrderManagementPage'
import SalOrderDetailPage from '@/pages/sal/SalOrderDetailPage'
import SalShipmentManagementPage from '@/pages/sal/SalShipmentManagementPage'
import SalPackingManagementPage from '@/pages/sal/SalPackingManagementPage'
import SalReturnManagementPage from '@/pages/sal/SalReturnManagementPage'
import SalSettlementManagementPage from '@/pages/sal/SalSettlementManagementPage'
import SalInvoiceManagementPage from '@/pages/sal/SalInvoiceManagementPage'
import SalPaymentManagementPage from '@/pages/sal/SalPaymentManagementPage'
import SalReconcileManagementPage from '@/pages/sal/SalReconcileManagementPage'
import { useAuthStore } from '@/store/auth'
import { lazy, Suspense } from 'react'

const ProdDashboard = lazy(() => import('@/pages/prod/Dashboard'))
const ProdExecute = lazy(() => import('@/pages/prod/verifications/Execute'))
const ProdVerificationList = lazy(() => import('@/pages/prod/verifications/List'))
const ProdVerificationDetail = lazy(() => import('@/pages/prod/verifications/Detail'))
const ProdEvidenceDetail = lazy(() => import('@/pages/prod/evidence/Detail'))
const ProdDossierList = lazy(() => import('@/pages/prod/dossiers/List'))
const ProdDossierDetail = lazy(() => import('@/pages/prod/dossiers/Detail'))
const ProdDossierSign = lazy(() => import('@/pages/prod/dossiers/Sign'))
const ProdCoreFreeze = lazy(() => import('@/pages/prod/CoreFreeze'))

const RelDashboard = lazy(() => import('@/pages/rel/Dashboard'))
const RelSealList = lazy(() => import('@/pages/rel/seals/List'))
const RelSealDetail = lazy(() => import('@/pages/rel/seals/Detail'))
const RelSealRequest = lazy(() => import('@/pages/rel/seals/Request'))
const RelSealCoSign = lazy(() => import('@/pages/rel/seals/CoSign'))
const RelGateList = lazy(() => import('@/pages/rel/gates/List'))
const RelSnapshotList = lazy(() => import('@/pages/rel/snapshots/List'))
const RelSnapshotDetail = lazy(() => import('@/pages/rel/snapshots/Detail'))
const RelDeclarationDetail = lazy(() => import('@/pages/rel/declarations/Detail'))
const RelReportDetail = lazy(() => import('@/pages/rel/reports/Detail'))
const RelRollbackList = lazy(() => import('@/pages/rel/rollback/List'))
const RelRollbackDetail = lazy(() => import('@/pages/rel/rollback/Detail'))
const RelRollbackDrill = lazy(() => import('@/pages/rel/rollback/Drill'))

const Lazy = ({ children }: { children: React.ReactNode }) => <Suspense fallback={null}>{children}</Suspense>

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated)
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }
  return <>{children}</>
}

const routes: RouteObject[] = [
  {
    path: '/login',
    element: <Login />,
  },
  {
    path: '/',
    element: (
      <ProtectedRoute>
        <MainLayout />
      </ProtectedRoute>
    ),
    children: [
      { index: true, element: <TenantManagement /> },
      { path: 'platform/tenants', element: <TenantManagement /> },
      { path: 'platform/placement', element: <PlacementManagement /> },
      { path: 'platform/backup', element: <BackupManagement /> },
      { path: 'tenant/hierarchy', element: <HierarchyManagement /> },
      { path: 'group/report', element: <GroupReport /> },
      { path: 'business/operations', element: <Operations /> },
      { path: 'business/master-data', element: <MasterDataManagement /> },
      { path: 'iam/users', element: <UserManagement /> },
      { path: 'inv/products', element: <ProductManagement /> },
      { path: 'inv/inventory/query', element: <InventoryQuery /> },
      { path: 'inv/inventory/transaction', element: <InventoryTransaction /> },
      { path: 'mdm/group-products', element: <GroupProductManagement /> },
      { path: 'mdm/group-categories', element: <GroupCategoryBrandPage /> },
      { path: 'mdm/spec-templates', element: <SpecTemplateManagement /> },
      { path: 'mdm/attribute-templates', element: <AttributeTemplateManagement /> },
      { path: 'mdm/enterprise-products', element: <EnterpriseProductManagement /> },
      { path: 'mdm/customizations', element: <EnterpriseCustomizationPage /> },
      { path: 'mdm/governance', element: <GovernanceManagement /> },
      { path: 'mdm/versions', element: <VersionManagement /> },
      { path: 'mdm/negative-policy', element: <NegativePolicyManagement /> },
      { path: 'mdm/master-data-query', element: <MasterDataQuery /> },
      { path: 'mdm/audit', element: <MasterDataAudit /> },
      { path: 'wms/space', element: <WmsSpaceManagementPage /> },
      { path: 'wms/inventory-positions', element: <WmsInventoryPositionsPage /> },
      { path: 'wms/receiving', element: <WmsReceivingPage /> },
      { path: 'wms/putaway', element: <WmsPutawayPage /> },
      { path: 'wms/picking', element: <WmsPickingPage /> },
      { path: 'wms/transfer', element: <WmsTransferPage /> },
      { path: 'wms/shipping', element: <WmsShippingPage /> },
      { path: 'wms/tasks', element: <WmsTaskManagementPage /> },
      { path: 'wms/reconcile', element: <WmsReconcilePage /> },
      { path: 'pur/suppliers', element: <PurSupplierManagementPage /> },
      { path: 'pur/quotations', element: <PurQuotationManagementPage /> },
      { path: 'pur/suppliers/evaluations', element: <PurSupplierEvaluationPage /> },
      { path: 'pur/requests', element: <PurRequestManagementPage /> },
      { path: 'pur/orders', element: <PurOrderManagementPage /> },
      { path: 'pur/orders/:id', element: <PurOrderDetailPage /> },
      { path: 'pur/receipts', element: <PurReceiptManagementPage /> },
      { path: 'pur/returns', element: <PurReturnManagementPage /> },
      { path: 'pur/settlements', element: <PurSettlementManagementPage /> },
      { path: 'pur/invoices', element: <PurInvoiceManagementPage /> },
      { path: 'pur/payments', element: <PurPaymentManagementPage /> },
      { path: 'pur/reconcile', element: <PurReconcileManagementPage /> },
      { path: 'sal/customers', element: <SalCustomerManagementPage /> },
      { path: 'sal/customer-categories', element: <SalCustomerCategoryPage /> },
      { path: 'sal/credit-limits', element: <SalCreditLimitPage /> },
      { path: 'sal/customer-pricing', element: <SalCustomerPricingPage /> },
      { path: 'sal/quotations', element: <SalQuotationManagementPage /> },
      { path: 'sal/orders', element: <SalOrderManagementPage /> },
      { path: 'sal/orders/:id', element: <SalOrderDetailPage /> },
      { path: 'sal/shipments', element: <SalShipmentManagementPage /> },
      { path: 'sal/packing', element: <SalPackingManagementPage /> },
      { path: 'sal/returns', element: <SalReturnManagementPage /> },
      { path: 'sal/settlements', element: <SalSettlementManagementPage /> },
      { path: 'sal/invoices', element: <SalInvoiceManagementPage /> },
      { path: 'sal/payments', element: <SalPaymentManagementPage /> },
      { path: 'sal/reconcile', element: <SalReconcileManagementPage /> },
      { path: 'prod/dashboard', element: <Lazy><ProdDashboard /></Lazy> },
      { path: 'prod/verifications/execute', element: <Lazy><ProdExecute /></Lazy> },
      { path: 'prod/verifications', element: <Lazy><ProdVerificationList /></Lazy> },
      { path: 'prod/verifications/:run_id', element: <Lazy><ProdVerificationDetail /></Lazy> },
      { path: 'prod/evidence/:evidence_id', element: <Lazy><ProdEvidenceDetail /></Lazy> },
      { path: 'prod/dossiers', element: <Lazy><ProdDossierList /></Lazy> },
      { path: 'prod/dossiers/:dossier_id', element: <Lazy><ProdDossierDetail /></Lazy> },

      { path: 'prod/dossiers/:dossier_id/sign', element: <Lazy><ProdDossierSign /></Lazy> },
      { path: 'prod/core-freeze', element: <Lazy><ProdCoreFreeze /></Lazy> },

      { path: 'rel/dashboard', element: <Lazy><RelDashboard /></Lazy> },
      { path: 'rel/seals', element: <Lazy><RelSealList /></Lazy> },
      { path: 'rel/seals/request', element: <Lazy><RelSealRequest /></Lazy> },
      { path: 'rel/seals/:releaseId', element: <Lazy><RelSealDetail /></Lazy> },
      { path: 'rel/seals/:releaseId/co-sign', element: <Lazy><RelSealCoSign /></Lazy> },
      { path: 'rel/gates/:releaseId', element: <Lazy><RelGateList /></Lazy> },
      { path: 'rel/snapshots/:releaseId', element: <Lazy><RelSnapshotList /></Lazy> },
      { path: 'rel/snapshots/:releaseId/:snapshotId', element: <Lazy><RelSnapshotDetail /></Lazy> },
      { path: 'rel/declarations/:releaseId', element: <Lazy><RelDeclarationDetail /></Lazy> },
      { path: 'rel/reports/:releaseId', element: <Lazy><RelReportDetail /></Lazy> },
      { path: 'rel/rollback', element: <Lazy><RelRollbackList /></Lazy> },
      { path: 'rel/rollback/:releaseId', element: <Lazy><RelRollbackDetail /></Lazy> },
      { path: 'rel/rollback/:releaseId/drill', element: <Lazy><RelRollbackDrill /></Lazy> },
    ],
  },
]

export const router = createBrowserRouter(routes)
