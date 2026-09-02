import { useState, useEffect } from 'react'
import { Card, Table, Tag } from 'antd'
import { pltApi } from '@/api/platform'

export default function MenuTreePage() {
  const [menus, setMenus] = useState<any[]>([])

  useEffect(() => {
    pltApi.permission.menu({ tenant_id: '' }).then(resp => setMenus(resp.data.items || []))
  }, [])

  return (
    <Card title="菜单树管理">
      <Table dataSource={menus} rowKey="menu_id" columns={[
        { title: '菜单名称', dataIndex: 'menu_name' },
        { title: '路径', dataIndex: 'menu_path' },
        { title: '权限码', dataIndex: 'permission_code' },
        { title: '排序', dataIndex: 'sort_order' },
        { title: '可见', dataIndex: 'visible', render: (v: boolean) => <Tag color={v ? 'green' : 'default'}>{v ? '是' : '否'}</Tag> },
      ]} />
    </Card>
  )
}