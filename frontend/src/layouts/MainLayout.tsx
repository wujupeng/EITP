import { Layout, Menu, theme } from 'antd'
import { Outlet, useLocation, useNavigate } from 'react-router-dom'
import type { MenuProps } from 'antd'

const { Header, Content, Sider } = Layout

const menuItems: MenuProps['items'] = [
  { key: '/platform/tenants', label: '平台运营' },
  { key: '/tenant/hierarchy', label: '租户管理' },
  { key: '/group/report', label: '集团报表' },
  { key: '/business/operations', label: '业务操作' },
]

export default function MainLayout() {
  const navigate = useNavigate()
  const location = useLocation()
  const { token: themeToken } = theme.useToken()

  const handleMenuClick: MenuProps['onClick'] = ({ key }) => {
    navigate(key)
  }

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Header style={{ display: 'flex', alignItems: 'center' }}>
        <div style={{ color: '#fff', fontSize: '18px', fontWeight: 'bold' }}>
          EITP Multi-Tenant 多企业统一进销存交易平台
        </div>
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