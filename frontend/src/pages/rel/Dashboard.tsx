import { useState, useEffect } from 'react'
import { Card, Row, Col, Statistic, Tag, Table } from 'antd'
import { relApi } from '@/api/rel'

export default function RelDashboardPage() {
  const [seals, setSeals] = useState<any[]>([])

  useEffect(() => {
    relApi.seal.list({ limit: 10 }).then(resp => setSeals(resp.data?.seals || []))
  }, [])

  const sealedCount = seals.filter(s => s.seal_status === 'SEALED').length
  const pendingCount = seals.filter(s => s.seal_status === 'PENDING_CO_SIGN').length
  const failedCount = seals.filter(s => s.seal_status?.includes('FAILED')).length

  const columns = [
    { title: '封版编号', dataIndex: 'release_number', key: 'release_number' },
    { title: '版本', dataIndex: 'version', key: 'version' },
    { title: 'Git Tag', dataIndex: 'git_tag', key: 'git_tag' },
    { title: '状态', dataIndex: 'seal_status', key: 'seal_status', render: (v: string) => {
      const color = v === 'SEALED' ? 'green' : v?.includes('FAILED') ? 'red' : 'blue'
      return <Tag color={color}>{v || 'UNKNOWN'}</Tag>
    }},
  ]

  return (
    <Card title="生产封版总览">
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={6}><Statistic title="已封版" value={sealedCount} valueStyle={{ color: '#3f8600' }} /></Col>
        <Col span={6}><Statistic title="待签发" value={pendingCount} valueStyle={{ color: '#d48806' }} /></Col>
        <Col span={6}><Statistic title="失败" value={failedCount} valueStyle={{ color: '#cf1322' }} /></Col>
        <Col span={6}><Statistic title="总计" value={seals.length} /></Col>
      </Row>
      <Table columns={columns} dataSource={seals} rowKey="release_id" pagination={{ pageSize: 10 }} />
    </Card>
  )
}