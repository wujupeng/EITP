import { Layout, Menu, theme, Space, Typography, Button, Dropdown } from 'antd'
import { Outlet, useLocation, useNavigate } from 'react-router-dom'
import type { MenuProps } from 'antd'
import { useAuthStore } from '@/store/auth'
import { client } from '@/api/client'

const { Header, Content, Sider } = Layout
const { Text } = Typography

const menuItems: MenuProps['items'] = [
  { key: '/platform/tenants', label: '平台运营' },
  { key: '/tenant/hierarchy', label: '租户管理' },
  { key: '/iam/users', label: '用户管理' },
  { key: '/inv/products', label: '商品管理' },
  { key: '/inv/inventory/query', label: '库存查询' },
  { key: '/inv/inventory/transaction', label: '库存事务' },
  {
    key: 'mdm',
    label: '主数据中心',
    children: [
      { key: '/mdm/group-products', label: '集团商品目录' },
      { key: '/mdm/group-categories', label: '集团分类品牌' },
      { key: '/mdm/spec-templates', label: '规格模板' },
      { key: '/mdm/attribute-templates', label: '属性模板' },
      { key: '/mdm/enterprise-products', label: '企业商品' },
      { key: '/mdm/customizations', label: '企业定制' },
      { key: '/mdm/governance', label: '治理工作流' },
      { key: '/mdm/versions', label: '版本管理' },
      { key: '/mdm/negative-policy', label: '负库存策略' },
      { key: '/mdm/master-data-query', label: '主数据查询' },
      { key: '/mdm/audit', label: '主数据审计' },
    ],
  },
  {
    key: 'wms',
    label: '仓储管理',
    children: [
      { key: '/wms/space', label: '仓储空间管理' },
      { key: '/wms/inventory-positions', label: '库存位置查询' },
      { key: '/wms/receiving', label: '收货作业台' },
      { key: '/wms/putaway', label: '上架作业台' },
      { key: '/wms/picking', label: '拣货作业台' },
      { key: '/wms/transfer', label: '移库作业台' },
      { key: '/wms/shipping', label: '发货作业台' },
      { key: '/wms/tasks', label: 'WMS Task 管理' },
      { key: '/wms/reconcile', label: '对账管理' },
    ],
  },
  { key: '/group/report', label: '集团报表' },
  { key: '/business/operations', label: '业务操作' },
]

export default function MainLayout() {
  const navigate = useNavigate()
  const location = useLocation()
  const { token: themeToken } = theme.useToken()
  const { username, tenantId, isTenantAdmin, logout, refreshToken } = useAuthStore()

  const handleMenuClick: MenuProps['onClick'] = ({ key }) => {
    navigate(key)
  }

  const handleLogout = async () => {
    try {
      await client.post('/auth/logout', { refresh_token: refreshToken })
    } catch {
      // ignore
    }
    logout()
    navigate('/login')
  }

  const userMenuItems: MenuProps['items'] = [
    { key: 'profile', label: username || '未登录', disabled: true },
    { key: 'tenant', label: `租户: ${tenantId ? tenantId.substring(0, 8) + '...' : '无'}`, disabled: true },
    { type: 'divider' },
    { key: 'logout', label: '退出登录', onClick: handleLogout },
  ]

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Header style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ color: '#fff', fontSize: '18px', fontWeight: 'bold' }}>
          EITP Multi-Tenant 多企业统一进销存交易平台
        </div>
        <Space>
          <Text style={{ color: isTenantAdmin ? '#52c41a' : '#fff' }}>
            {username || '未登录'}
          </Text>
          <Dropdown menu={{ items: userMenuItems }} placement="bottomRight">
            <Button size="small">账户</Button>
          </Dropdown>
        </Space>
      </Header>
      <Layout>
        <Sider width={220} style={{ background: themeToken.colorBgContainer }}>
          <Menu
            mode="inline"
            selectedKeys={[location.pathname]}
            items={menuItems}
            onClick={handleMenuClick}
            style={{ height: '100%', borderRight: 0 }}
          />
        </Sider>
        <Content style={{ padding: '24px', background: themeToken.colorBgContainer }}>
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  )
}
