import { useState, useEffect } from 'react'
import { Card, Table, Tag, Button } from 'antd'
import { relApi } from '@/api/rel'
import { useNavigate } from 'react-router-dom'

export default function RelSealListPage() {
  const [seals, setSeals] = useState<any[]>([])
  const navigate = useNavigate()

  useEffect(() => {
    relApi.seal.list().then(resp => setSeals(resp.data?.seals || []))
  }, [])

  const columns = [
    { title: '封版编号', dataIndex: 'release_number', key: 'release_number' },
    { title: '版本', dataIndex: 'version', key: 'version' },
    { title: 'Git Tag', dataIndex: 'git_tag', key: 'git_tag' },
    { title: '状态', dataIndex: 'seal_status', key: 'seal_status', render: (v: string) => {
      const color = v === 'SEALED' ? 'green' : v?.includes('FAILED') ? 'red' : 'blue'
      return <Tag color={color}>{v}</Tag>
    }},
    { title: '裁决', dataIndex: 'verdict', key: 'verdict', render: (v: string) => v ? <Tag color={v === 'FINAL_PASS' ? 'green' : 'red'}>{v}</Tag> : '-' },
    { title: '操作', key: 'action', render: (_: any, record: any) => (
      <Button type="link" onClick={() => navigate(`/rel/seals/${record.release_id}`)}>详情</Button>
    )},
  ]

  return (
    <Card title="封版记录列表" extra={<Button type="primary" onClick={() => navigate('/rel/seals/request')}>发起封版</Button>}>
      <Table columns={columns} dataSource={seals} rowKey="release_id" pagination={{ pageSize: 20 }} />
    </Card>
  )
}