import { useState, useEffect } from 'react'
import { Card, Table, Tag, Button } from 'antd'
import { relApi } from '@/api/rel'
import { useNavigate } from 'react-router-dom'

export default function RelRollbackListPage() {
  const [declarations, setDeclarations] = useState<any[]>([])
  const navigate = useNavigate()

  useEffect(() => {
    relApi.declaration.list().then(resp => setDeclarations(resp.data?.declarations || []))
  }, [])

  const columns = [
    { title: '封版ID', dataIndex: 'release_id', key: 'release_id' },
    { title: '声明状态', dataIndex: 'declaration_status', key: 'declaration_status', render: (v: string) => (
      <Tag color={v === 'EFFECTIVE' ? 'green' : 'orange'}>{v}</Tag>
    )},
    { title: '操作', key: 'action', render: (_: any, record: any) => (
      <Button type="link" onClick={() => navigate(`/rel/rollback/${record.release_id}`)}>查看回滚方案</Button>
    )},
  ]

  return (
    <Card title="回滚方案列表">
      <Table columns={columns} dataSource={declarations} rowKey="declaration_id" pagination={{ pageSize: 20 }} />
    </Card>
  )
}