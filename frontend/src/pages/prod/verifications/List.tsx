import { useState, useEffect } from 'react'
import { Card, Table, Tag, Select, Button, Space } from 'antd'
import { prodApi } from '@/api/prod'
import { useNavigate } from 'react-router-dom'

export default function ProdVerificationListPage() {
  const [data, setData] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [filters, setFilters] = useState<any>({})
  const navigate = useNavigate()

  const loadData = async () => {
    setLoading(true)
    try {
      const resp = await prodApi.verification.list({ ...filters, limit: 100 })
      setData(resp.data?.items || [])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { loadData() }, [])

  const columns = [
    { title: 'Run ID', dataIndex: 'run_id', key: 'run_id', render: (v: string) => 
      <a onClick={() => navigate(`/prod/verifications/${v}`)}>{v.slice(0, 8)}...</a> },
    { title: '验证项', dataIndex: 'verification_item', key: 'verification_item' },
    { title: '状态', dataIndex: 'status', key: 'status', render: (v: string) => {
      const color = v === 'COMPLETED' ? 'green' : v === 'FAILED' ? 'red' : 'blue'
      return <Tag color={color}>{v}</Tag>
    }},
    { title: '结论', dataIndex: 'conclusion', key: 'conclusion', render: (v: string) => {
      const color = v === 'PASS' ? 'green' : v === 'FAIL' ? 'red' : 'orange'
      return v ? <Tag color={color}>{v}</Tag> : '-'
    }},
    { title: '执行人', dataIndex: 'executor', key: 'executor' },
    { title: '环境', dataIndex: 'environment', key: 'environment' },
    { title: '创建时间', dataIndex: 'created_at', key: 'created_at' },
  ]

  return (
    <Card title="验证执行列表">
      <Space style={{ marginBottom: 16 }}>
        <Select placeholder="验证项" allowClear style={{ width: 200 }}
          onChange={v => setFilters({ ...filters, verification_item: v })}
          options={[
            { label: 'V01 性能基线', value: 'V01_BASELINE' },
            { label: 'V02 并发用户', value: 'V02_CONCURRENT' },
          ]} />
        <Select placeholder="结论" allowClear style={{ width: 120 }}
          onChange={v => setFilters({ ...filters, conclusion: v })}
          options={[
            { label: 'PASS', value: 'PASS' },
            { label: 'FAIL', value: 'FAIL' },
            { label: 'INCONCLUSIVE', value: 'INCONCLUSIVE' },
          ]} />
        <Button type="primary" onClick={loadData}>查询</Button>
      </Space>
      <Table columns={columns} dataSource={data} rowKey="run_id" loading={loading} />
    </Card>
  )
}