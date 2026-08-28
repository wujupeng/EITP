import { createBrowserRouter, type RouteObject } from 'react-router-dom'
import MainLayout from '@/layouts/MainLayout'
import TenantManagement from '@/pages/platform/TenantManagement'
import PlacementManagement from '@/pages/platform/PlacementManagement'
import BackupManagement from '@/pages/platform/BackupManagement'
import HierarchyManagement from '@/pages/tenant/HierarchyManagement'
import GroupReport from '@/pages/group/GroupReport'
import Operations from '@/pages/business/Operations'
import MasterDataManagement from '@/pages/business/MasterDataManagement'

const routes: RouteObject[] = [
  {
    path: '/',
    element: <MainLayout />,
    children: [
      { index: true, element: <TenantManagement /> },
      { path: 'platform/tenants', element: <TenantManagement /> },
      { path: 'platform/placement', element: <PlacementManagement /> },
      { path: 'platform/backup', element: <BackupManagement /> },
      { path: 'tenant/hierarchy', element: <HierarchyManagement /> },
      { path: 'group/report', element: <GroupReport /> },
      { path: 'business/operations', element: <Operations /> },
      { path: 'business/master-data', element: <MasterDataManagement /> },
    ],
  },
]

export const router = createBrowserRouter(routes)