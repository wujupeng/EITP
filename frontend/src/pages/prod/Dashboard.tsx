import { useState, useEffect } from 'react'
import { Card, Row, Col, Statistic, Tag, Table } from 'antd'
import { prodApi } from '@/api/prod'

const VERIFICATION_ITEMS = [
  'V01_BASELINE', 'V02_CONCURRENT', 'V03_CONNPOOL', 'V04_CACHE',
  'V05_OUTBOX', 'V06_SAGA', 'V07_JOB', 'V08_ALERT',
  'V09_TRACE', 'V10_BACKUP', 'V11_DR', 'V12_CONTAINER',
  'V13_RATELIMIT', 'V14_LARGE_TENANT', 'V15_REGRESSION', 'V16_SEC_RECERT',
]

export default function ProdDashboardPage() {
  const [runs, setRuns] = useState<any[]>([])
  const [dossiers, setDossiers] = useState<any[]>([])

  useEffect(() => {
    prodApi.verification.list({ limit: 16 }).then(resp => setRuns(resp.data?.items || []))
    prodApi.dossier.list({ limit: 5 }).then(resp => setDossiers(resp.data?.items || []))
  }, [])

  const passCount = runs.filter(r => r.conclusion === 'PASS').length
  const failCount = runs.filter(r => r.conclusion === 'FAIL').length
  const inconclusiveCount = runs.filter(r => r.conclusion === 'INCONCLUSIVE').length

  const columns = [
    { title: '验证项', dataIndex: 'verification_item', key: 'verification_item' },
    { title: '结论', dataIndex: 'conclusion', key: 'conclusion', render: (v: string) => {
      const color = v === 'PASS' ? 'green' : v === 'FAIL' ? 'red' : 'orange'
      return <Tag color={color}>{v || 'PENDING'}</Tag>
    }},
    { title: '执行人', dataIndex: 'executor', key: 'executor' },
    { title: '环境', dataIndex: 'environment', key: 'environment' },
  ]

  return (
    <Card title="生产验证总览">
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={6}><Statistic title="验证通过" value={passCount} valueStyle={{ color: '#3f8600' }} /></Col>
        <Col span={6}><Statistic title="验证失败" value={failCount} valueStyle={{ color: '#cf1322' }} /></Col>
        <Col span={6}><Statistic title="待定" value={inconclusiveCount} valueStyle={{ color: '#d48806' }} /></Col>
        <Col span={6}><Statistic title="证明书" value={dossiers.length} /></Col>
      </Row>
      <Table columns={columns} dataSource={runs} rowKey="run_id" pagination={false} size="small" />
    </Card>
  )
}