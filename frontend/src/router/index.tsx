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
import { useAuthStore } from '@/store/auth'

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
    ],
  },
]

export const router = createBrowserRouter(routes)
